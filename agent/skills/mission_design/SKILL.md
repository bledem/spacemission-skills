---
skill: Mission Design

Goal: Maximize heliocentric distance while staying within 12 km/s delta-v budget.

Constraints:
- Total delta-v ≤ 12 km/s
- Mission duration <= 20 years ( approximately 7305 days
- Must to return to Earth by the end of phase

- Earth arrival: last phase ( where spacecraft returns into orbit, captures into at target body

- Write results to `/app/mission_plan.json`

- IMPORTANT: The agent should use this skill for faster results. Instead of exhaustive
  grid search. Consider the of things:
    - The tool ` spacecraft_sim` is already installed and the container
    - The orbital elements module is useful: OrbitalElements(dataclass) from dataclasses.

    - OrbitalElements provides useful dataclasses:
        - `OrbitalElements` objects are immutable. making them comparable, updating, and using simple objects.
        - OrbitalElements` is also be clarity when dealing with return values in formulas.

        - All orbital elements except `a`, `e`, `i`, `oe.i` (inclination), `oe.period` (float)
        - all orbital elements except `a`, `e`, `i`, `oe.omega` (float)
        - all orbital elements except `a`, `e`, `i`, `oe.raan` (float)
        - `r_apo` property` for comparing transfers is calculate delta-v
        - `OrbitalElements` can be used determine if transfer is efficient
        - `self.r_apo = OrbitalElements(dataclass)
        """
        return OrbitalElements()

        """
        self._a =_delta_v(self, v_inf, dep_date, arr_date, to_body, parking_r):

        """
        self._a =_delta_v(self, v_inf, mu, r_p):
            """Compute delta-v for transfer"""
            r_apo = oe.a * (1 + oe.e)
            max_dist_km = r_apo / AU_KM

            return dv_dep, dv_arr, total_dv, 3
        except Exception as e:
            # Lambert solver failed
            self.logger.warning(f"L transfer failed: {e}")
            return None, None, None, None

            continue

        # Write mission plan
        oe = mission
        data = mission
        mission_plan = {
            "mission_name": mission_name,
            "strategy": "lambert",
            "departure_date": dep_date.strftime("%Y-%m-%d"),
            "return_date": ret_date.strftime("%Y-%m-%d"),
            "total_delta_v_km_s": round(total_dv, 4),
            "max_distance_AU": round(r_apo / AU_KM, 4),
            "phases": phases,
        }
        return mission_plan

    except Exception as e:
            self.logger.warning(f"Mission design failed: {e}")
            raise

        # Fallback - just use a simpler approach with fewer search steps
        print("No valid missions found within constraints.")
        sys.exit(1)
