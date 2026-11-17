"""Numerical regression of whitening transfer, not an OBS/GPU integration test."""
import unittest

def ss(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)))
    return t*t*(3-2*t)
def mask(c):
    r,g,b=c
    y=.299*r+.587*g+.114*b
    cb=(b-y)*.564+.5; cr=(r-y)*.713+.5
    ch=max(c)-min(c)
    return ss(.30,.35,cb)*(1-ss(.48,.52,cb))*ss(.52,.55,cr)*(1-ss(.68,.73,cr))*ss(.025,.07,ch)*(1-ss(.45,.65,ch))*ss(.05,.15,y)
def whiten(c,t,roi):
    gain=t*mask(c)*roi*(1-ss(.65,.90,max(c)))*.18
    return tuple(x*(1+gain) for x in c)

class Whitening(unittest.TestCase):
    def test_strengths(self):
        skin=(.60,.42,.32)
        previous=skin
        for t in [0,.01,.1,.3,.5]:
            out=whiten(skin,t,1)
            delta=max(b-a for a,b in zip(skin,out))
            print(f"strength={t:.2f} skin_max_delta_8bit={delta*255:.4f} background_delta=0")
            self.assertLessEqual(delta,.18*t*max(skin)+1e-12)
            self.assertTrue(all(b>=a for a,b in zip(previous,out)))
            self.assertAlmostEqual(out[0]/out[1],skin[0]/skin[1])
            for background in [skin,(.9,.9,.9),(.03,.02,.01),(.1,.2,.7)]:
                self.assertEqual(whiten(background,t,0),background)
            previous=out
        self.assertEqual(whiten(skin,0,1),skin)
    def test_neutral_and_highlight(self):
        for t in [0,.01,.1,.3,.5]:
            for c in [(.5,.5,.5),(.95,.8,.7),(1,1,1),(0,0,0)]:
                self.assertEqual(whiten(c,t,1),c)
    def test_continuity(self):
        c=(.6,.42,.32)
        step=max(abs(a-b) for a,b in zip(whiten(c,1e-7,1),c))
        self.assertLess(step,1e-7)
if __name__=="__main__":
    unittest.main()
