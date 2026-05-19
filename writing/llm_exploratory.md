Here is a **compact literature review** using **peer-reviewed papers only**.

Large language models (LLMs) are increasingly being studied as tools for the **exploratory phase of research**: generating hypotheses, proposing research ideas, surfacing overlooked connections in the literature, and helping researchers navigate large design spaces. A recent peer-reviewed review in *Nature Reviews Methods Primers* argues that LLMs are beginning to affect multiple stages of the scientific method, especially ideation, literature synthesis, and experiment planning, but that their scientific value depends on grounding, evaluation, and human oversight. ([Nature][1])

The strongest evidence so far is for **idea and hypothesis generation**, not fully autonomous discovery of robust new algorithms. In psychology, Tong et al. showed that combining LLMs with causal knowledge graphs can support automated hypothesis generation from the literature, with outputs aligned to meaningful psychological constructs rather than simple text recombination. This is important because it frames LLMs as exploratory engines that can suggest candidate explanations or research directions for experts to test, rather than as standalone discoverers. ([Nature][2])

In computer science, peer-reviewed conference work provides more direct evidence that LLMs can generate **novel research ideas**. Si, Yang, and Hashimoto’s ICLR 2025 study compared ideas from an LLM ideation agent against ideas from more than 100 NLP researchers and found that LLM-generated ideas were judged **more novel**, though somewhat less feasible. Follow-up work in EMNLP 2025 extended this line by studying LLM idea generation across multiple domains and showing that LLMs can produce research proposals judged to be original, but still struggle with practical constraints, evaluation rigor, and downstream execution. Another EMNLP 2025 paper, *Chain of Ideas*, showed that structuring retrieved literature before prompting improves ideation quality, suggesting that exploratory performance depends heavily on how the model is connected to prior work rather than on raw model size alone. ([OpenReview][3])

Beyond pure ideation, several peer-reviewed studies place LLMs in **discovery-oriented scientific workflows**. In neuroscience, Luo et al. reported in *Nature Human Behaviour* that LLMs could predict experimental outcomes better than human experts in their benchmark, indicating that domain-tuned language models may help prioritize promising hypotheses before costly experiments. In medicine and biomedicine, peer-reviewed work has shown that LLM-based systems can accelerate evidence synthesis and clinical literature search, which matters for exploratory studies because faster and broader synthesis can expose non-obvious research opportunities. Taken together, these studies suggest that LLMs currently add the most value as **ranking, synthesis, and proposal systems** inside a human-led discovery loop. ([Nature][4])

For **finding new algorithms**, the peer-reviewed evidence is still limited. The literature is much stronger on LLMs as assistants for ideation, planning, coding, and search over candidate methods than on LLMs independently discovering broadly accepted, novel algorithms that outperform the state of the art in a durable way. Even the latest high-profile work on end-to-end AI research automation emphasizes that performance improves when models are embedded in structured pipelines with retrieval, verification, experimentation, and review; this supports the view that algorithmic discovery is more likely to come from **LLM-centered research systems** than from prompting a standalone chatbot. So, the current peer-reviewed consensus is that LLMs are already useful for **exploratory science**, but claims about them autonomously inventing genuinely new algorithms remain ahead of the strongest validated evidence. ([Nature][5])

## Takeaway

A fair summary of the peer-reviewed literature is:

**LLMs are already credible tools for exploratory research**—especially for hypothesis generation, research ideation, literature-based discovery, and prioritizing experiments—but **evidence for reliable autonomous discovery of genuinely new algorithms is still emerging**. Today, their best-supported role is as a **creative, retrieval-augmented partner** inside a human verification loop, not as an independent scientific discoverer. ([Nature][1])

## Peer-reviewed references

1. Zhang, Y. et al. “Exploring the role of large language models in the scientific method: from hypothesis to discovery.” *Nature Reviews Methods Primers* (2025). ([Nature][1])
2. Tong, S. et al. “Automating psychological hypothesis generation with AI.” *Humanities and Social Sciences Communications* (2024). ([Nature][2])
3. Si, C., Yang, D., & Hashimoto, T. “Can LLMs Generate Novel Research Ideas? A Large-Scale Human Study with 100+ NLP Researchers.” *ICLR 2025*. ([OpenReview][3])
4. Kumar, S. et al. “Can Large Language Models Unlock Novel Scientific Research Ideas?” *EMNLP 2025*. ([ACL Anthology][6])
5. Li, L. et al. “Chain of Ideas: Revolutionizing Research Via Novel Idea Development with LLM Agents.” *Findings of EMNLP 2025*. ([ACL Anthology][7])
6. Luo, X. et al. “Large language models surpass human experts in predicting neuroscience results.” *Nature Human Behaviour* (2025). ([Nature][4])
7. Wang, Z. et al. “Accelerating clinical evidence synthesis with large language models.” *npj Digital Medicine* (2025). ([Nature][8])
8. Shi, X. et al. “Evidence triangulator: using large language models to automate evidence triangulation.” *Nature Communications* (2025). ([Nature][9])
9. Lu, C. et al. “Towards end-to-end automation of AI research.” *Nature* (2026). ([Nature][5])

I can also turn this into a **conference-paper style related work section** with academic tone and in-text citations only.

[1]: https://www.nature.com/articles/s44387-025-00019-5?utm_source=chatgpt.com "Exploring the role of large language models in the scientific ..."
[2]: https://www.nature.com/articles/s41599-024-03407-5?utm_source=chatgpt.com "Automating psychological hypothesis generation with AI"
[3]: https://openreview.net/forum?id=M23dTGWCZy&utm_source=chatgpt.com "Can LLMs Generate Novel Research Ideas? A Large- ..."
[4]: https://www.nature.com/articles/s41562-024-02046-9?utm_source=chatgpt.com "Large language models surpass human experts in ..."
[5]: https://www.nature.com/articles/s41586-026-10265-5?utm_source=chatgpt.com "Towards end-to-end automation of AI research"
[6]: https://aclanthology.org/2025.emnlp-main.1704/?utm_source=chatgpt.com "Can Large Language Models Unlock Novel Scientific ..."
[7]: https://aclanthology.org/2025.findings-emnlp.477/?utm_source=chatgpt.com "Chain of Ideas: Revolutionizing Research Via Novel ..."
[8]: https://www.nature.com/articles/s41746-025-01840-7.pdf?utm_source=chatgpt.com "Accelerating clinical evidence synthesis with large ..."
[9]: https://www.nature.com/articles/s41467-025-62783-x?utm_source=chatgpt.com "Evidence triangulator: using large language models to ..."
