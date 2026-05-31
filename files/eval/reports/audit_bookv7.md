# Outline + Content Audit -- `files/output/bookv7.state.json`

- Topic: `Large Language Models`
- Sections scored: 150

## Topic drift (titles < 0.45 cosine to topic)

| Section | Title | Cosine |
|---|---|---|
| `3.3` | Comparative Analysis of Gemma and Gemini Performance Benchmarks | 0.399 |
| `10.10` | Monitoring, Logging, and Drift Detection in Production | 0.412 |
| `5.6` | Comparison of LoRA, QLoRA, and Adapter Methods | 0.417 |
| `8.10` | Emerging Benchmarks and Future Directions in Hallucination Research | 0.417 |
| `1.4` | Decoder-Only vs. Encoder-Decoder Architectures | 0.418 |
| `14.7` | Medical Symptom Triage and Differential Diagnosis | 0.42 |
| `15.8` | Ethical Implications of Autonomous Swarms and Algorithmic Governance | 0.426 |
| `3.4` | The Open-Source Strategy: Gemma's Licensing and Community Ecosystem | 0.427 |
| `9.7` | Deployment Diagrams for Hybrid Cloud Strategies | 0.43 |
| `3.9` | Cost Efficiency and Inference Latency: Gemma vs. Gemini API | 0.434 |
| `1.10` | From Static Pre-training to Instruction Tuning | 0.44 |
| `4.1` | Data Sourcing Strategies and Licensing Compliance | 0.44 |
| `10.1` | Quantization Fundamentals and Hardware Alignment | 0.444 |
| `13.1` | Multimodal Architecture Fundamentals: Encoder-Decoder and Transformer Fusion | 0.449 |

## Title near-duplicates (cosine >= 0.85)

None.
## Content duplicates (cosine >= 0.80 on first 1500 chars)

| A | B | Cosine |
|---|---|---|
| `5.1` | `5.2` | 0.89 |
| `7.7` | `15.2` | 0.875 |
| `7.7` | `15.1` | 0.873 |
| `6.5` | `6.8` | 0.857 |
| `6.9` | `7.1` | 0.854 |
| `6.5` | `7.3` | 0.846 |
| `7.5` | `10.4` | 0.843 |
| `3.5` | `3.8` | 0.84 |
| `3.2` | `3.7` | 0.838 |
| `11.2` | `11.5` | 0.838 |
| `6.3` | `6.4` | 0.836 |
| `2.1` | `2.2` | 0.835 |
| `11.2` | `11.3` | 0.834 |
| `5.8` | `5.9` | 0.833 |
| `5.2` | `5.6` | 0.832 |
| `6.1` | `7.1` | 0.831 |
| `5.6` | `5.7` | 0.826 |
| `3.5` | `3.6` | 0.825 |
| `12.1` | `12.6` | 0.824 |
| `3.2` | `3.3` | 0.823 |
| `5.1` | `5.6` | 0.823 |
| `6.3` | `6.5` | 0.823 |
| `1.5` | `1.10` | 0.821 |
| `2.7` | `10.2` | 0.821 |
| `3.6` | `3.7` | 0.819 |
| `3.3` | `3.10` | 0.815 |
| `3.3` | `3.7` | 0.814 |
| `12.7` | `13.9` | 0.814 |
| `3.3` | `3.8` | 0.813 |
| `11.5` | `13.8` | 0.812 |
| `13.2` | `13.7` | 0.81 |
| `8.8` | `8.10` | 0.807 |
| `15.1` | `15.2` | 0.806 |
| `3.7` | `3.8` | 0.805 |
| `6.1` | `6.9` | 0.804 |
| `6.6` | `7.3` | 0.804 |
| `8.3` | `8.8` | 0.804 |
| `8.4` | `8.9` | 0.803 |
| `2.1` | `2.9` | 0.801 |
| `6.5` | `6.9` | 0.801 |
| `6.3` | `6.8` | 0.8 |
| `6.8` | `7.3` | 0.8 |

## Verdict

- Topic drift sections: **14**
- Title clusters: **0**
- Content duplicate pairs: **42**

**NEEDS ATTENTION** -- outline or content has duplication / drift issues.