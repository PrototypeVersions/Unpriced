from pathlib import Path
import sys
from datetime import datetime, timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import engine
from scripts.audit_session import audit_missing, status_lines


def synthetic_market():
    rng=np.random.default_rng(20261102)
    dates=pd.bdate_range('2023-01-03', periods=850)
    symbols=engine.UNIVERSE[:22] + [engine.BENCHMARK,'QQQ','SMH','XLF','XLE','XLV','XLI','XLU','^VIX','^TNX']
    frames={}
    common=rng.normal(0.00025,0.009,len(dates))
    for i,s in enumerate(symbols):
        if s=='^VIX':
            values=np.maximum(11,18+np.cumsum(rng.normal(0,0.15,len(dates))))
        elif s=='^TNX':
            values=np.maximum(1,4+np.cumsum(rng.normal(0,0.01,len(dates))))
        else:
            idio=rng.normal(0.0001+(i%5)*0.00002,0.010+(i%4)*0.001,len(dates))
            ret=0.45*common+0.55*idio
            values=100*np.exp(np.cumsum(ret))
        volume=rng.lognormal(mean=16,sigma=.35,size=len(dates))
        frames[s]=pd.DataFrame({'Open':values,'High':values*1.004,'Low':values*.996,'Close':values,'Volume':volume},index=dates)
    return frames


def main():
    session=engine.nyse_session('2026-11-02')
    assert session is not None
    assert session['open'].hour==9 and session['open'].minute==30
    assert session['close'].hour==16 and session['close'].minute==0

    frames=synthetic_market()
    close,volume=engine.align_panel(frames,list(frames))
    panel=engine.make_feature_panel(close,volume)
    target=engine.attach_targets(panel,close,5)
    dates=sorted(close[engine.BENCHMARK].dropna().index)
    safe=set(pd.Timestamp(x) for x in dates[:-6])
    train=target[target['date'].isin(safe)]
    models=engine.fit_models(train)
    current=panel[panel['date']==panel['date'].max()]
    preds=engine.predict_current(models,current,{'broad_logit':.45,'boosted':.35,'momentum_logit':.20})
    assert len(preds)>=15
    assert all(0<=p['pOutperform']<=1 for p in preds)
    assert all(.5<=p['directionProbability']<=1 for p in preds)

    state=engine.compute_market_state(close,'2026-11-02')
    assert state['status']=='live'
    assert 0<=state['metrics']['breadthAbove20dMA']<=1

    prop=engine.compute_propagation(close,'2026-11-02')
    assert prop['status']=='live'
    assert prop['method']=='empirical-lead-lag-v1'

    # A delayed scheduler must never backdate a premarket gate or a paper fill.
    with TemporaryDirectory() as temporary:
        late=datetime(2026,11,4,15,36,tzinfo=engine.TZ)
        with patch.object(engine,'STATES',Path(temporary)), patch.object(engine,'now_et',return_value=late):
            engine.premarket_mode()
            engine.execute_mode()
            assert (Path(temporary)/'2026-11-04-premarket-missed.json').exists()
            assert (Path(temporary)/'2026-11-04-execution-missed.json').exists()
            assert not (Path(temporary)/'2026-11-04-execution.json').exists()

    # A code-push recovery may not publish during the 35-minute settlement buffer.
    with TemporaryDirectory() as temporary:
        with patch.object(engine,'FORECASTS',Path(temporary)), patch.object(
            engine,'now_et',return_value=datetime(2026,11,4,16,20,tzinfo=engine.TZ)
        ):
            engine.postclose_mode()
            assert not list(Path(temporary).glob('*.json'))

    # Never substitute an unfinished 09:35 candle for the completed 09:30 bar.
    incomplete=pd.DataFrame({'High':[101.0],'Low':[99.0],'Close':[100.0]},
        index=pd.DatetimeIndex(['2026-11-04 09:35'],tz=engine.TZ))
    assert engine.first_bar_typical_price(incomplete,'2026-11-04') is None
    # A delayed or dropped GitHub schedule must leave an honest observed miss,
    # even when no original schedule job existed to write its own miss file.
    session = {
        'open': datetime(2026, 11, 11, 9, 30, tzinfo=engine.TZ),
        'close': datetime(2026, 11, 11, 16, 0, tzinfo=engine.TZ),
    }
    observed = datetime(2026, 11, 11, 16, 36, tzinfo=engine.TZ)
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        states, forecasts = root / 'states', root / 'forecasts'
        created = audit_missing(observed, session, states)
        assert {p.name for p in created} == {
            '2026-11-11-premarket-missed.json',
            '2026-11-11-execution-missed.json',
        }
        first_record = (states / '2026-11-11-execution-missed.json').read_bytes()
        assert __import__('json').loads(first_record)['at'] == observed.isoformat()
        assert not audit_missing(observed + timedelta(hours=1), session, states)
        assert (states / '2026-11-11-execution-missed.json').read_bytes() == first_record
        lines, warnings = status_lines(observed, session, states, forecasts)
        assert len(warnings) == 3  # both missed windows and missing close
        assert any('35-minute settlement' in line for line in lines)

    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        states, forecasts = root / 'states', root / 'forecasts'
        states.mkdir()
        forecasts.mkdir()
        import json
        (states / '2026-11-11-premarket.json').write_text(json.dumps({
            'asOf': '2026-11-11T08:46:00-05:00'
        }))
        (states / '2026-11-11-execution.json').write_text(json.dumps({
            'at': '2026-11-11T09:36:00-05:00'
        }))
        (forecasts / '2026-11-11-close.json').write_text(json.dumps({
            'publishedAt': '2026-11-11T16:35:21-05:00'
        }))
        assert not audit_missing(observed, session, states)
        lines, warnings = status_lines(observed, session, states, forecasts)
        assert not warnings
        assert any('0m 21s after 16:35 ET target' in line for line in lines)
        (forecasts / '2026-11-11-close.json').write_text(json.dumps({
            'publishedAt': '2026-11-11T16:34:59-05:00'
        }))
        _, warnings = status_lines(observed, session, states, forecasts)
        assert any('precedes the settlement boundary' in s for s in warnings)

    # Before the 09:45 hard cutoff, no execution miss may be invented.
    with TemporaryDirectory() as temporary:
        states = Path(temporary)
        early = datetime(2026, 11, 11, 9, 40, tzinfo=engine.TZ)
        created = audit_missing(early, session, states)
        assert [p.name for p in created] == ['2026-11-11-premarket-missed.json']
        assert not (states / '2026-11-11-execution-missed.json').exists()

    print('UNPRICED model and schedule guard smoke tests passed')


if __name__=='__main__':
    main()
