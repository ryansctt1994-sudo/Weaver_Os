import unittest, math
from hydro import *
class HydroTests(unittest.TestCase):
    def test_endpoints(self):
        for a,v in [(0,0),(90,.5),(180,1)]: self.assertAlmostEqual(cap_factor(a),v)
    def test_bounds_monotonic(self):
        vs=[cap_factor(i/10) for i in range(1801)]
        self.assertTrue(all(0<=v<=1 for v in vs))
        self.assertTrue(all(a<=b for a,b in zip(vs,vs[1:])))
    def test_domains(self):
        for x in [-1,181,float('nan'),float('inf'),True]:
            with self.assertRaises(ValueError): cap_factor(x)
        with self.assertRaises(ValueError): attenuation(1e6,-1)
        with self.assertRaises(ValueError): standing_wave(0,.001)
    def test_db_conversion(self):
        self.assertAlmostEqual(attenuation(1e6,.01)['loss_db'],.002171472409516259)
        self.assertAlmostEqual(attenuation(2e6,.01)['loss_db'],.008685889638065036)
    def test_attenuation_scaling(self):
        a=attenuation(1e6,.01); b=attenuation(2e6,.01)
        self.assertAlmostEqual(b['loss_db'],4*a['loss_db'])
        self.assertAlmostEqual(a['intensity_ratio'],a['amplitude_ratio']**2)
        self.assertEqual(attenuation(1e6,0)['loss_db'],0)
    def test_spacing(self):
        a=standing_wave(4e6,200e-6)
        self.assertAlmostEqual(a['half_wavelength_m'],185e-6)
        self.assertAlmostEqual(a['half_wavelengths_across_width'],200/185)
    def test_volume(self):
        self.assertAlmostEqual(droplet_volume(10e-6)['volume_pL'],math.pi/6)
    def test_force_convention(self):
        p=force_comparison(1e-6,2e6,1,.1,.001,1e-4)
        n=force_comparison(1e-6,2e6,1,-.1,.001,1e-4)
        self.assertAlmostEqual(p['radiation_peak_n'],4*math.pi*1e-18*(2*math.pi*2e6/1480)*.1,delta=1e-25)
        self.assertEqual(p['radiation_peak_n'],n['radiation_peak_n'])
        self.assertEqual(n['contrast_sign'],-1)
    def test_force_scale_and_gates(self):
        a=force_comparison(1e-6,2e6,1,.1,.001,1e-4)
        b=force_comparison(2e-6,2e6,1,.1,.001,1e-4)
        self.assertAlmostEqual(b['radiation_peak_n']/a['radiation_peak_n'],8)
        self.assertAlmostEqual(b['drag_n']/a['drag_n'],2)
        with self.assertRaises(ValueError): force_comparison(.001,2e6,1,.1,.001,1e-4)
        with self.assertRaises(ValueError): force_comparison(1e-6,2e6,1,.1,.001,1)
    def test_contrast(self):
        self.assertEqual(contrast(1000,1000,1,1),0)
    def test_receipt(self):
        a=seal_prediction({'f':1},{'loss':2})
        self.assertEqual(a,seal_prediction({'f':1},{'loss':2}))
        self.assertNotEqual(a['sha256'],seal_prediction({'f':2},{'loss':2})['sha256'])
        self.assertFalse(a['packet']['measurement'])
if __name__=='__main__': unittest.main()
