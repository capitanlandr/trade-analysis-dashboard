# Three-way Rank Comparison — DynastyProcess vs KeepTradeCut vs FantasyCalc

_Generated 2026-08-12. Read-only analysis; scale-free rank comparison across three dynasty value sources._

## Sources & philosophy (one line each)
- **DynastyProcess (DP)** = analyst opinion — a deterministic exponential curve over FantasyPros Superflex ECR (`value_2qb ≈ 10295·exp(−0.0234·ecr)`, R²=0.9997). No market signal; slowest to react.
- **KeepTradeCut (KTC)** = stated preference — crowd keep/trade/cut survey votes (0–9999 cap). What the community *says* it would do.
- **FantasyCalc (FC)** = revealed preference — implied values from ~1M real completed trades. What the market *actually does*; fastest to react, noisier for illiquid players.

All three configured to SF / 2QB dynasty. DP = `values.csv value_2qb` (scrape 2026-08-07); KTC = latest SF value per player from `ktc_history.csv` (through 2026-08-10); FC = live API pull.

## Coverage
| Source | Valued players |
|---|---|
| DynastyProcess (value_2qb) | 761 |
| KeepTradeCut (SF, latest>0) | 366 |
| FantasyCalc (SF dynasty PPR) | 475 |
| **DP ∩ KTC** | 363 |
| **DP ∩ FC** | 452 |
| **KTC ∩ FC** | 350 |
| **3-way intersection** | 349 |

## Pairwise rank correlations
| Pair | N (intersection) | Spearman ρ | Kendall τ |
|---|---|---|---|
| DP – KTC | 363 | 0.965 | 0.855 |
| DP – FC | 452 | 0.969 | 0.854 |
| KTC – FC | 350 | 0.977 | 0.878 |

**Read:** The two market sources (KTC, FC) agree with each other most (ρ=0.977) — both are crowd/market signals. Each market source correlates less with the analyst ECR curve (DP). This is the core finding: *market ≈ market > market vs analyst.*

## Biggest 3-way rank spread (max rank − min rank, within the 349-player intersection)
| Player | DP rank | KTC rank | FC rank | Spread |
|---|---|---|---|---|
| Brandon Aiyuk | 135 | 318 | 233 | 183 |
| Tyreek Hill | 151 | 325 | 236 | 174 |
| Anthony Richardson Sr. | 107 | 249 | 216 | 142 |
| Cyrus Allen | 269 | 223 | 177 | 92 |
| Aaron Rodgers | 168 | 253 | 181 | 85 |
| Malik Benson | 318 | 340 | 262 | 78 |
| Deshaun Watson | 190 | 263 | 186 | 77 |
| Kirk Cousins | 223 | 258 | 184 | 74 |
| Tua Tagovailoa | 102 | 176 | 132 | 74 |
| Roman Wilson | 344 | 271 | 299 | 73 |
| Geno Smith | 159 | 229 | 167 | 70 |
| Jalen Milroe | 290 | 224 | 244 | 66 |
| Riley Leonard | 345 | 300 | 279 | 66 |
| Ricky Pearsall | 124 | 187 | 161 | 63 |
| Matt Hibner | 306 | 345 | 282 | 63 |


## FantasyCalc most BULLISH vs the DP/KTC consensus
_(fc_vs_consensus = avg(DP,KTC) rank − FC rank; positive = FC ranks the player higher/better)_
| Player | DP rank | KTC rank | FC rank | FC−consensus |
|---|---|---|---|---|
| Cyrus Allen | 269 | 223 | 177 | 69.0 |
| Malik Benson | 318 | 340 | 262 | 67.0 |
| Kirk Cousins | 223 | 258 | 184 | 56.5 |
| Barion Brown | 329 | 305 | 270 | 47.0 |
| Riley Leonard | 345 | 300 | 279 | 43.5 |
| Matt Hibner | 306 | 345 | 282 | 43.5 |
| Joe Flacco | 346 | 344 | 302 | 43.0 |
| Alvin Kamara | 228 | 238 | 191 | 42.0 |
| Deshaun Watson | 190 | 263 | 186 | 40.5 |
| CJ Daniels | 312 | 335 | 283 | 40.5 |


## FantasyCalc most BEARISH vs the DP/KTC consensus
| Player | DP rank | KTC rank | FC rank | FC−consensus |
|---|---|---|---|---|
| Chris Brazzell II | 203 | 204 | 253 | -49.5 |
| Kevin Coleman Jr. | 253 | 242 | 295 | -47.5 |
| Cedric Tillman | 265 | 286 | 322 | -46.5 |
| Elijah Sarratt | 176 | 171 | 220 | -46.5 |
| Jaylin Noel | 173 | 182 | 219 | -41.5 |
| Kaytron Allen | 206 | 194 | 240 | -40.0 |
| Cole Kmet | 273 | 259 | 304 | -38.0 |
| Anthony Richardson Sr. | 107 | 249 | 216 | -38.0 |
| Luke Musgrave | 333 | 291 | 349 | -37.0 |
| Emmett Johnson | 185 | 198 | 228 | -36.5 |


## Market (KTC+FC) vs analyst (DP) — youth/upside thesis test
### Market ranks MUCH higher than DP (market loves youth/upside)
| Player | DP rank | KTC rank | FC rank |
|---|---|---|---|
| Cyrus Allen | 269 | 223 | 177 |
| Roman Wilson | 344 | 271 | 299 |
| Jalen Milroe | 290 | 224 | 244 |
| Riley Leonard | 345 | 300 | 279 |
| Jaydon Blue | 263 | 212 | 208 |
| Malik Washington | 234 | 173 | 192 |
| Ja'Kobi Lane | 205 | 163 | 152 |
| Dont'e Thornton Jr. | 316 | 260 | 278 |
| LeQuint Allen Jr. | 300 | 243 | 265 |
| Tank Bigsby | 219 | 169 | 178 |


### DP ranks MUCH higher than market (ECR still rewards proven vets)
| Player | DP rank | KTC rank | FC rank |
|---|---|---|---|
| Brandon Aiyuk | 135 | 318 | 233 |
| Tyreek Hill | 151 | 325 | 236 |
| Anthony Richardson Sr. | 107 | 249 | 216 |
| Tua Tagovailoa | 102 | 176 | 132 |
| Ricky Pearsall | 124 | 187 | 161 |
| Aaron Rodgers | 168 | 253 | 181 |
| Jauan Jennings | 163 | 211 | 210 |
| Oscar Delp | 198 | 236 | 249 |
| Garrett Nussmeier | 258 | 311 | 291 |
| Devaughn Vele | 274 | 314 | 315 |

