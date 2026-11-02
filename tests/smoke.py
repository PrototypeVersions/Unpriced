import numpy as np
import pandas as pd

import engine


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
    print('UNPRICED model smoke test passed')


if __name__=='__main__':
    main()
