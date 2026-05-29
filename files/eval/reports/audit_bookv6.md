# Outline + Content Audit -- `files/output/bookv6.state.json`

- Topic: `Large Language Models`
- Sections scored: 150

## Topic drift (titles < 0.45 cosine to topic)

| Section | Title | Cosine |
|---|---|---|
| `5.7` | Comparative Analysis: RLHF vs. DPO Performance | 0.381 |
| `1.6` | Encoder-Decoder vs. Decoder-Only Designs | 0.391 |
| `13.3` | Mitigation Strategies for Hallucinations and Fabrication | 0.429 |
| `14.8` | Copyright, Plagiarism, and Intellectual Property Challenges | 0.429 |
| `10.3` | Parameter-Efficient Fine-Tuning (PEFT) Techniques for Industry Deployment | 0.435 |
| `5.5` | Stability Challenges in RLHF Training | 0.44 |
| `10.10` | Case Studies in Vertical Success: Healthcare, Law, and Financial Analytics | 0.446 |
| `11.6` | Neuro-Symbolic Integration: Bridging Neural Flexibility with Symbolic Rigor | 0.449 |

## Title near-duplicates (cosine >= 0.85)

### Cluster 1 (max pair cosine 0.898)

- `1.7` -- Scaling Laws and Computational Complexity
- `2.4` -- Scaling Laws and Compute Efficiency

## Content duplicates (cosine >= 0.80 on first 1500 chars)

| A | B | Cosine |
|---|---|---|
| `5.6` | `5.7` | 0.916 |
| `4.2` | `9.4` | 0.902 |
| `7.3` | `10.7` | 0.897 |
| `11.9` | `12.4` | 0.883 |
| `1.9` | `11.1` | 0.874 |
| `5.6` | `5.10` | 0.874 |
| `5.7` | `5.8` | 0.873 |
| `5.6` | `5.8` | 0.869 |
| `5.8` | `15.5` | 0.869 |
| `1.7` | `9.5` | 0.865 |
| `1.9` | `4.7` | 0.865 |
| `2.9` | `11.1` | 0.861 |
| `5.8` | `5.10` | 0.861 |
| `2.7` | `9.3` | 0.86 |
| `2.9` | `3.7` | 0.857 |
| `3.7` | `11.1` | 0.851 |
| `8.4` | `8.9` | 0.851 |
| `4.1` | `5.1` | 0.85 |
| `5.7` | `5.10` | 0.848 |
| `7.3` | `7.4` | 0.847 |
| `1.9` | `2.9` | 0.846 |
| `11.3` | `11.4` | 0.84 |
| `8.6` | `8.7` | 0.839 |
| `7.4` | `10.7` | 0.837 |
| `2.5` | `7.2` | 0.835 |
| `5.2` | `5.10` | 0.834 |
| `5.1` | `5.2` | 0.833 |
| `5.7` | `15.5` | 0.833 |
| `5.6` | `15.5` | 0.832 |
| `1.7` | `7.2` | 0.83 |
| `12.5` | `12.9` | 0.828 |
| `5.10` | `15.5` | 0.827 |
| `4.5` | `5.1` | 0.823 |
| `2.9` | `4.7` | 0.822 |
| `6.3` | `6.4` | 0.822 |
| `6.9` | `9.5` | 0.822 |
| `4.7` | `11.1` | 0.821 |
| `1.10` | `4.10` | 0.82 |
| `7.7` | `7.8` | 0.818 |
| `5.4` | `5.6` | 0.817 |
| `2.4` | `3.8` | 0.816 |
| `4.7` | `11.3` | 0.816 |
| `5.6` | `5.9` | 0.816 |
| `2.4` | `3.3` | 0.815 |
| `4.7` | `11.7` | 0.814 |
| `3.2` | `3.3` | 0.812 |
| `5.9` | `12.7` | 0.811 |
| `8.3` | `8.4` | 0.811 |
| `11.2` | `11.3` | 0.811 |
| `13.2` | `13.8` | 0.811 |

## Verdict

- Topic drift sections: **8**
- Title clusters: **1**
- Content duplicate pairs: **65**

**NEEDS ATTENTION** -- outline or content has duplication / drift issues.