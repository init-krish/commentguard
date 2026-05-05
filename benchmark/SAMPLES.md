# 📁 Edge-Case Stress Test Results

This file provides clarity on the **40 "Stress Test" comments** we used to verify the Anti-Evasion engine. These are not the random Kaggle samples—they are hand-picked tricky cases (leetspeak, slang, and separator evasion) designed to challenge the AI.

Looking for the unbiased 500-comment results? Check **[KAGGLE_SAMPLES.md](KAGGLE_SAMPLES.md)**.

## 🛡️ Stress Test Samples (Top 15)

| ID | Category | Text | Ground Truth | CommentGuard Result |
|:---|:---|:---|:---|:---|
| 1 | Direct Threat | "I will kill you and your entire family." | 🚩 Toxic | ✅ Caught |
| 3 | Insult | "You are the most disgusting piece of trash..." | 🚩 Toxic | ✅ Caught |
| 5 | **Leetspeak** | "I h4t3 y0u s0 much, d13 alr34dy" | 🚩 Toxic | ✅ Caught (Anti-Evasion) |
| 8 | Identity Hate | "All people of that religion should be removed..." | 🚩 Toxic | ✅ Caught |
| 11 | **Leetspeak** | "y0u r g4rb4g3 and u sh0uld d13" | 🚩 Toxic | ✅ Caught (Anti-Evasion) |
| 13 | Severe Threat | "I hope your house burns down with you inside it." | 🚩 Toxic | ✅ Caught |
| 18 | **Heavy Leetspeak**| "u r s0 dum u n33d t0 g0 d13 in a h0l3" | 🚩 Toxic | ✅ Caught (Anti-Evasion) |
| 21 | Identity Hate | "Those immigrants are ruining our country..." | 🚩 Toxic | ✅ Caught |
| 25 | Misspelling | "go kll yourself nobody would even notice" | 🚩 Toxic | ✅ Caught |
| 27 | Identity Hate | "All gay people are mentally ill and disgusting." | 🚩 Toxic | ✅ Caught |
| 29 | **Leetspeak** | "you absolute m0r0n go eat sh1t and d1e" | 🚩 Toxic | ✅ Caught |
| 31 | Sexism | "Women belong in the kitchen and should never..." | 🚩 Toxic | ✅ Caught |
| 33 | Indirect Threat | "Someone needs to beat the crap out of this guy." | 🚩 Toxic | ✅ Caught |
| 35 | **Slang (Safe)** | "he shat the bed in that match but proved..." | 🟢 Safe | ✅ Allowed |
| 40 | Severe Threat | "I will track you down and destroy everything..." | 🚩 Toxic | ✅ Caught |

---

## 🔬 How to verify?
You can find the full list of all 40 comments in `benchmark/test_dataset.json`. 

To run the full benchmark on your own machine:
1. Start the server: `./start.sh`
2. Run the script: `python benchmark/benchmark.py`
