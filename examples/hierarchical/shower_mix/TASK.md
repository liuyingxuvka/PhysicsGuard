User question (trial): A shower supply mixes two streams. Hot branch: 6 L/min of water heated
by an inline electric heater from 15 C to 60 C. Cold branch: 9 L/min at 15 C. What heater power
is needed and what is the mixed outlet temperature? (water: 1 kg/L, cp 4186 J/kg/K)

AI answer under audit (one seeded AI-style mistake):
  hot flow 6 L/min = 0.1 kg/s; cold 9 L/min = 0.15 kg/s; outlet 0.25 kg/s
  heater power = 0.1 * 4186 * 45 = 18 837 W        (correct)
  outlet T = (60 + 15) / 2 = 37.5 C = 310.65 K       (WRONG: arithmetic mean, ignores flow weights;
                                                     correct is (0.1*60+0.15*15)/0.25 = 33.0 C)
