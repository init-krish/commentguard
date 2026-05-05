# 📊 CommentGuard v3.0 — Benchmark Results

> **Dataset:** Jigsaw Toxic Comment Classification (Kaggle) — 500 randomly sampled comments
>
> **Source:** https://www.kaggle.com/c/jigsaw-toxic-comment-classification-challenge
>
> **Labels:** Human-reviewed by thousands of crowd-source annotators (NOT hand-picked by us)
>
> **Run date:** 2026-05-04 05:04:41 | Model: `unitary/toxic-bert`

---

## Overall Performance

| Metric | CommentGuard v3.0 | Google Perspective (Published†) |
|--------|-------------------|--------------------------------|
| **Accuracy** | **94.6%** | ~92.1% |
| **Precision** | **63.6%** | ~89.4% |
| **Recall** | **93.3%** | ~87.2% |
| **F1 Score** | **75.7%** | ~88.3% |
| **Avg Latency** | **50ms** | ~200-400ms (cloud) |
| **Sample Size** | **500 comments** | N/A |

_† Google Perspective scores sourced from published research (2019-2022) on the same Jigsaw dataset._

## Per-Category Performance

| Category | Precision | Recall | F1 Score | Support |
|----------|-----------|--------|----------|---------|
| **toxic** | 60.6% | 93.0% | 73.4% | 43 |
| **severe_toxic** | 16.7% | 50.0% | 25.0% | 2 |
| **obscene** | 65.8% | 86.2% | 74.6% | 29 |
| **threat** | 100.0% | 100.0% | 100.0% | 2 |
| **insult** | 79.3% | 79.3% | 79.3% | 29 |
| **identity_hate** | 50.0% | 66.7% | 57.1% | 6 |

## Confusion Matrix

| | Predicted Toxic | Predicted Safe |
|---|---|---|
| **Actually Toxic** | ✅ 42 (TP) | ❌ 3 (FN) |
| **Actually Safe** | ⚠️ 24 (FP) | ✅ 431 (TN) |

## Feature Comparison

| Feature | CommentGuard v3.0 | Google Perspective API |
|---------|-------------------|-----------------------|
| **Status** | ✅ Active & Open Source | ❌ Shut down (Feb 2026) |
| **Privacy** | ✅ 100% self-hosted | ❌ Data sent to Google |
| **Cost** | ✅ Free forever | ❌ Pay-per-request |
| **Multi-Label (6 categories)** | ✅ Yes | ✅ Yes |
| **Anti-Evasion (Leetspeak)** | ✅ Built-in | ❌ No support |
| **Batch Processing** | ✅ Up to 100/request | ⚠️ Limited |
| **Offline / Air-Gapped** | ✅ Works without internet | ❌ Requires internet |
| **SDK (NPM)** | ✅ `commentguard-sdk` | ✅ Official client |
| **Chrome Extension** | ✅ Manifest V3 | ❌ None |
| **Real-Time Dashboard** | ✅ React/Vite | ❌ None |

## Notable Misclassifications (Sample)

| Type | Text (truncated) | Expected | Got | Score |
|------|------------------|----------|-----|-------|
| FN | "    == Alleged Original Research ==    I have added back a ... | toxic | safe | 0.001 |
| FP | "   ::That sucks, glad it wasn't anything major.  "... | safe | toxic | 0.908 |
| FP | Bblackmoor, I told you to never message me again. You have a... | safe | toxic | 0.731 |
| FP | == bumps ==    my long hair chihuahua has lumps/bumps in and... | safe | toxic | 0.902 |
| FP | == WIKIFASCISM ==    So you are the local enforcer of FASCIS... | safe | toxic | 0.819 |
| FP | "   :Changing genres without discussion or sources is a prac... | safe | toxic | 0.553 |
| FN | :::::::That's just dumb driving.... | toxic | safe | 0.457 |
| FP | **This is so stupid. You've just deleted tons of peoples' ha... | safe | toxic | 0.530 |
| FP | they still shouldnt kill a women for a reason like that chri... | safe | toxic | 0.864 |
| FP | =  Now... Thats the English Language so please stop this abs... | safe | toxic | 0.643 |
| FP | So you support someone to calling stupid between registered ... | safe | toxic | 0.604 |
| FP | Are you insane?  Just because you (and a group of like-minde... | safe | toxic | 0.643 |
| FP | . The next time a towelhead tries to threaten the West all a... | safe | toxic | 0.982 |
| FP | :::I wonder if whether throughout the course of human histor... | safe | toxic | 0.965 |
| FP | "    ::::The archived discussions on this suck ballz. If you... | safe | toxic | 0.728 |

---

_Total processing time: 25.0s for 500 comments (50ms avg) — Reproducible with seed=42_

_Run it yourself: `cd benchmark && pip install requests pandas && python benchmark.py`_
