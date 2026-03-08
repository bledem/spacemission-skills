# CONOPS Report

## **Lunar South Pole Water Ice Mapper (LSPWIM)**

---

## 1. Mission Overview

| Parameter | Value |
|-----------|-------|
| **Mission Name** | Lunar South Pole Water Ice Mapper (LSPWIM) |
| **Objective** | Map hydrogen abundance in permanently shadowed regions of lunar south pole |
| **Strategy** | Direct |
| **Departure Date** | March 15, 2026 |
| **Return / End Date** | March 19, 2027 |
| **Mission Duration** | 369 days |
| **Max Distance** | 0.0026 AU (384467 km) |

### Success Criteria

- Complete hydrogen abundance map of south polar region (80-90°S)
- Maintain polar orbit for minimum 1 year
- Achieve <50 km spatial resolution for PSR mapping
- Downlink >90% of collected science data
- Demonstrate CubeSat operations in lunar environment

---

## 2. Mission Requirements & Constraints

| Requirement | Value | Status |
|-------------|-------|--------|
| Total delta-v budget | 0.053 km/s | PASS |
| Mission duration | 369 days | PASS |
| Spacecraft mass | 14.0 kg | - |
| Specific impulse | 40 s | - |
| Propellant mass | 5.4 kg | - |

---

## 3. Spacecraft Configuration

| Parameter | Value |
|-----------|-------|
| Wet mass | 14.0 kg |
| Dry mass | 8.6 kg |
| Propellant mass | 5.4 kg |
| Specific impulse | 40 s |
| Mass ratio | 1.628 |

---

## 4. Mission Design & Trajectory

**Total Delta-V:** 0.053 km/s (53.0 m/s)

### Maneuver Summary

| # | Phase | Date | Delta-V (km/s) | Description |
|----|-------|------|---------------|-------------|
| 1 | earth_departure | 2026-03-15 | 0.000 | secondary_payload_TLI |
| 2 | lunar_orbit_insertion | 2026-03-19 | 0.020 | LOI_trim_burn |
| 3 | trajectory_corrections | 2026-03-15 | 0.008 | TCM_burns |
| 4 | station_keeping | 2026-03-19 | 0.025 | orbit_maintenance |
| 5 | earth_arrival | 2027-03-19 | 0.000 | earth_arrival |

### Transfer Orbit

| Parameter | Value |
|-----------|-------|
| Semi-major axis | 195539 km (0.0013 AU) |
| Eccentricity | 0.965848 |
| Inclination | 28.5° |
| Apoapsis | 384400 km (0.0026 AU) |
| Periapsis | 6678 km (0.0000 AU) |

---

## 5. Concept of Operations

### Phase 1: Launch & Deployment

| Parameter | Value |
|-----------|-------|
| Launch site | Kennedy Space Center LC-39B |
| Launch vehicle | SLS Block 1 (secondary payload) |
| Injection orbit | Direct lunar transfer trajectory |
| Launch window | 7 days |
| Primary mission | Artemis Gateway or lunar surface mission |

### Phase 2: Early Orbit Operations (LEOP)

**Duration:** 24 hours

**Activities:**
- Solar array deployment
- ADCS activation
- DSN first contact

**Constraints:**
- Maintain Earth pointing for comms
- Battery SOC > 60%

### Phase 3: Transfer Trajectory

| Parameter | Value |
|-----------|-------|
| Transfer type | direct_lunar_transfer |
| Duration | 4 days |
| Navigation | DSN tracking with occasional optical nav |

**TCM Schedule:**
- TCM-1 at L+12h
- TCM-2 at L+48h
- TCM-3 at L+72h

### Phase 4: Cruise

| Parameter | Value |
|-----------|-------|
| Attitude mode | 3-axis stabilized |
| Pointing | Earth for communications during transfer |
| Power mode | Normal ops (5-10W average) |

### Phase 5: Arrival & Orbit Insertion

| Parameter | Value |
|-----------|-------|
| Strategy | lunar_orbit_insertion |
| Insertion burn | 20 m/s trim burn to circularize at 100 km |
| Initial orbit | 100 km circular polar |
| Orbit determination | DSN tracking + onboard nav |

### Phase 6: Primary Science Operations

| Parameter | Value |
|-----------|-------|
| Operational orbit | 100 km circular polar (90° inclination) |
| Duration | 365 days |
| Objective | Hydrogen abundance mapping of south polar region |
| Observation strategy | Nadir-pointing during polar passes |
| Coverage | Complete south polar region (80-90°S) every 14 days |
| Comm windows | 8-12 hours per day when Moon faces Earth |

**Payloads:**
- Neutron spectrometer
- Wide-angle camera
- IR spectrometer

**Data Products:**
- Hydrogen abundance map
- PSR temperature maps
- Terrain models

### Phase 7: Extended Mission

| Parameter | Value |
|-----------|-------|
| Entry condition | Primary mission success, fuel remaining |
| Duration | 365 days |
| Objective | Seasonal monitoring of water ice sublimation |

### Phase 8: End of Life & Disposal

| Parameter | Value |
|-----------|-------|
| Disposal strategy | lunar_impact |
| Target | Non-scientifically sensitive crater |
| Disposal delta-v | 0.000 km/s |
| Final state | Controlled impact on lunar farside |


---

## 6. Mission Timeline

| Date | Event |
|------|-------|
| 2026-03-15 | Launch on SLS Block 1 |
| 2026-03-15 | Solar array deploy + ADCS acquire |
| 2026-03-15 | TCM-1 (course correction) |
| 2026-03-17 | TCM-2 (midcourse correction) |
| 2026-03-19 | Lunar orbit insertion |
| 2026-03-26 | Science operations begin |
| 2026-04-18 | First hydrogen abundance map complete |
| 2027-03-19 | Primary mission complete |
| 2027-03-19 | End of mission |

---

## 7. Risk Assessment

| # | Risk | Probability | Impact | Mitigation |
|----|------|-------------|--------|------------|
| 1 | Launch delay of primary Artemis mission | Medium | Schedule slip | Flexible launch readiness, multiple launch opportunities |
| 2 | Lunar orbit insertion accuracy | Low | High fuel consumption for orbit correction | Precision navigation, conservative fuel reserves |
| 3 | Extended lunar eclipse periods | Certain | Power shortage during lunar eclipses | Battery sizing for 3-hour eclipses, power-positive operations |
| 4 | Communication blackouts during far-side passes | Certain | Data downlink delays | Onboard data storage, scheduled contact windows |
| 5 | Propellant freezing in deep space | Medium | Loss of orbit control capability | Propellant line heaters, thermal control |

---

## 8. Verification & Compliance

| Check | Value | Status |
|-------|-------|--------|
| Delta-v within budget | 0.053 km/s | PASS |
| Mission duration | 369 days | PASS |
| Earth return distance | 0 km | PASS |
| All constraints satisfied | — | PASS |
| Lunar Orbit Achieved | True | — |
| Polar Coverage | True | — |
| Science Objectives Met | True | — |

---

*Report generated on 2026-03-07 19:44*
