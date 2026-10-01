"""GOFB-HYDRO v0.1. SI inputs; model predictions, never measurements."""
import math, json, hashlib

def domain(x, name, positive=False):
    if isinstance(x, bool) or not isinstance(x, (int,float)) or not math.isfinite(x) or x < 0 or (positive and x == 0):
        raise ValueError(name + ': invalid physical input')
    return x

def cap_factor(angle_deg):
    domain(angle_deg, 'angle_deg')
    if angle_deg > 180: raise ValueError('angle outside [0,180]')
    c=math.cos(math.radians(angle_deg))
    return (2+c)*(1-c)**2/4

def attenuation(frequency_hz, length_m, coefficient=25e-15):
    """Assumed amplitude absorption coefficient; excludes walls and scattering."""
    domain(frequency_hz,'frequency_hz',True)
    domain(length_m,'length_m')
    domain(coefficient,'coefficient')
    alpha=coefficient*frequency_hz**2
    return dict(alpha_np_m=alpha, loss_db=20/math.log(10)*alpha*length_m,
                amplitude_ratio=math.exp(-alpha*length_m),
                intensity_ratio=math.exp(-2*alpha*length_m))

def standing_wave(frequency_hz, width_m, sound_speed_m_s=1480):
    for name,x in [('frequency',frequency_hz),('width',width_m),('sound_speed',sound_speed_m_s)]:
        domain(x,name,True)
    spacing=sound_speed_m_s/(2*frequency_hz)
    return dict(half_wavelength_m=spacing, half_wavelengths_across_width=width_m/spacing,
                fundamental_frequency_hz=sound_speed_m_s/(2*width_m))

def droplet_volume(diameter_m):
    domain(diameter_m,'diameter',True)
    v=math.pi*diameter_m**3/6
    return dict(volume_m3=v, volume_pL=v*1e15)

def contrast(rho_p, rho_f, beta_p, beta_f):
    for x in [rho_p,rho_f,beta_p,beta_f]: domain(x,'material property',True)
    return ((5*rho_p-2*rho_f)/(2*rho_p+rho_f)-beta_p/beta_f)/3

def force_comparison(radius_m, frequency_hz, energy_j_m3, phi, viscosity_pa_s,
                     relative_speed_m_s, sound_speed_m_s=1480, fluid_density=1000):
    """Peak inviscid radiation force vs low-Re Stokes drag.
    Relative speed is supplied, not a prediction of acoustic streaming.
    Selected approximation gates are ka<=0.1 and Re<=0.1.
    """
    for x in [radius_m,frequency_hz,viscosity_pa_s,sound_speed_m_s,fluid_density]:
        domain(x,'positive parameter',True)
    domain(energy_j_m3,'energy'); domain(relative_speed_m_s,'speed')
    if isinstance(phi,bool) or not isinstance(phi,(float,int)) or not math.isfinite(phi): raise ValueError('contrast')
    k=2*math.pi*frequency_hz/sound_speed_m_s
    re=2*radius_m*relative_speed_m_s*fluid_density/viscosity_pa_s
    if k*radius_m > .1 or re > .1: raise ValueError('approximation gate failed')
    rad=4*math.pi*radius_m**3*k*energy_j_m3*abs(phi)
    drag=6*math.pi*viscosity_pa_s*radius_m*relative_speed_m_s
    return dict(radiation_peak_n=rad,drag_n=drag,peak_ratio=rad/drag if drag else None,
                contrast_sign=(phi>0)-(phi<0),ka=k*radius_m,reynolds=re)

def seal_prediction(inputs, outputs):
    packet=dict(schema='gofb-hydro-v0.1',evidence_kind='MODEL_PREDICTION',
                measurement=False,inputs=inputs,outputs=outputs)
    encoded=json.dumps(packet,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    return dict(packet=packet,sha256=hashlib.sha256(encoded).hexdigest())

def demo():
    inputs=dict(attenuation=dict(frequency_hz=2e6,length_m=.01,coefficient=25e-15),
                standing_wave=dict(frequency_hz=4e6,width_m=200e-6,sound_speed_m_s=1480),
                droplet=dict(diameter_m=10e-6),cap=dict(angle_deg=90),
                force=dict(radius_m=1e-6,frequency_hz=2e6,energy_j_m3=1,phi=.1,
                           viscosity_pa_s=.001,relative_speed_m_s=1e-4,
                           sound_speed_m_s=1480,fluid_density=1000))
    outputs=dict(attenuation=attenuation(**inputs['attenuation']),
                 standing_wave=standing_wave(**inputs['standing_wave']),
                 droplet=droplet_volume(**inputs['droplet']),cap=cap_factor(**inputs['cap']),
                 force=force_comparison(**inputs['force']))
    return seal_prediction(inputs,outputs)

if __name__=='__main__': print(json.dumps(demo(),indent=2,allow_nan=False))
