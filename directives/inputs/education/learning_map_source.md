# SCAIO AI Learning Map

_Canonical structure for the education series. Exported from Jimmy's Claude doc (PDF, 2026-10-15); links are the doc's own._

## The three levels

- **Curious:** You want to understand what people are talking about. No math, no code. Plain-language explainers, short videos, SCAIO primers.
- **Practitioner:** You use AI at work or make decisions about it. You want to know how things work, where they fail, and what questions to ask.
- **Builder:** You want to build, evaluate, or govern AI systems directly. Courses, technical documentation, papers.

## 1. Foundations

Foundations covers what machine learning is and the ideas every other branch builds on.

### Subtopics

- What AI is (and isn't)
  - AI vs. machine learning vs. deep learning vs. generative AI
  - Narrow vs. general AI
  - A short history: symbolic AI, AI winters, the deep learning era
- How machines learn
  - Training data, features, and labels
  - Supervised, unsupervised, and reinforcement learning
  - Overfitting, generalization, and test sets
- Neural networks
  - Neurons, layers, and weights
  - Gradient descent and backpropagation
  - Convolutional and recurrent networks
- The math underneath
  - Linear algebra: vectors and matrices
  - Calculus: derivatives and gradients
  - Probability and statistics
- Reinforcement learning
  - Agents, rewards, and policies
  - Game-playing systems (AlphaGo) to robotics

### Where to learn

- Curious
  - [Elements of AI (University of Helsinki)](https://www.elementsofai.com/)
  - [3Blue1Brown: Neural Networks](https://www.3blue1brown.com/topics/neural-networks)
  - [StatQuest](https://www.youtube.com/@statquest)
- Practitioner
  - [Google Machine Learning Crash Course](https://developers.google.com/machine-learning/crash-course)
  - [Machine Learning Specialization (Andrew Ng, Coursera)](https://www.coursera.org/specializations/machine-learning-introduction) (Free to audit)
  - [Kaggle Learn](https://www.kaggle.com/learn) (Short hands-on lessons)
- Builder
  - [Practical Deep Learning for Coders (fast.ai)](https://course.fast.ai/)
  - [Dive into Deep Learning](https://d2l.ai/) (Free textbook with code)
  - [Mathematics for Machine Learning](https://mml-book.github.io/) (Free textbook)
  - [Khan Academy: Linear Algebra](https://www.khanacademy.org/math/linear-algebra)
  - [Deep Learning (Goodfellow, Bengio, Courville)](https://www.deeplearningbook.org/) (Free to read online)
  - [Reinforcement Learning: An Introduction (Sutton and Barto)](http://incompleteideas.net/book/the-book-2nd.html) (Free PDF from the authors)

## 2. How LLMs work

This branch explains the large language models behind today's chatbots: how they are built, trained, and why they behave the way they do.

### Subtopics

- The basics
  - Tokens, context windows, and next-token prediction
  - Parameters and model size
  - Embeddings: meaning as numbers
- The transformer
  - Attention and self-attention
  - Why transformers replaced earlier architectures
- Training
  - Pretraining on large text corpora
  - Fine-tuning and instruction tuning
  - Reinforcement learning from human feedback (RLHF) and constitutional methods
  - Scaling laws: data, compute, and parameters
- Capabilities and limits
  - Reasoning models and test-time compute
  - Hallucination and why it happens
  - Knowledge cutoffs and grounding
- Beyond text
  - Multimodal models: images, audio, video
  - Diffusion models for image and video generation
- Open vs. closed models
  - Open-weight models and what "open" means
  - Model cards and system cards
- Interpretability
  - Looking inside models: features and circuits

### Where to learn

- Curious
  - [SCAIO primer: What is an LLM?](learn/primer-01-llm.html)
  - [Intro to Large Language Models (Andrej Karpathy)](https://www.youtube.com/watch?v=zjkBMFhNj_g) (1-hour talk)
  - [3Blue1Brown: Neural Networks](https://www.3blue1brown.com/topics/neural-networks) (Later chapters cover transformers and attention)
- Practitioner
  - [The Illustrated Transformer (Jay Alammar)](https://jalammar.github.io/illustrated-transformer/)
  - [Hugging Face LLM Course](https://huggingface.co/learn/llm-course)
  - [Lil'Log (Lilian Weng)](https://lilianweng.github.io/) (Technical explainers)
- Builder
  - [Neural Networks: Zero to Hero (Karpathy)](https://karpathy.ai/zero-to-hero.html) (Build a GPT from scratch)
  - [Stanford CS224N: NLP with Deep Learning](https://web.stanford.edu/class/cs224n/)
  - [Attention Is All You Need (2017)](https://arxiv.org/abs/1706.03762)
  - [Scaling Laws for Neural Language Models (2020)](https://arxiv.org/abs/2001.08361)
  - [Training Compute-Optimal Large Language Models (Chinchilla, 2022)](https://arxiv.org/abs/2203.15556)
  - [Training language models to follow instructions (InstructGPT, 2022)](https://arxiv.org/abs/2203.02155)
  - [Constitutional AI (2022)](https://arxiv.org/abs/2212.08073)
  - [Transformer Circuits (Anthropic interpretability research)](https://transformer-circuits.pub/)

## 3. Using AI

Using AI is about getting real value from the tools and knowing when not to trust them. It is the most useful starting branch for most readers.

### Subtopics

- The tool landscape
  - General assistants: ChatGPT, Claude, Gemini, Copilot
  - Search and research tools
  - Image, voice, and video generators
  - AI inside existing software (Office, Google Workspace, CRMs)
- Prompting
  - Giving context, examples, and constraints
  - Breaking big tasks into steps
  - Reusable instructions, projects, and custom assistants
- Judging output
  - Fact-checking and citations
  - Spotting hallucinations and overconfidence
  - Knowing which tasks AI handles well and which it doesn't
- Using AI at work
  - Writing, summarizing, and analysis
  - Data and spreadsheets
  - Workflow automation
- Responsible use
  - What not to paste in: privacy and confidential data
  - Disclosure and attribution
  - Organizational AI-use policies

### Where to learn

- Curious
  - [SCAIO primer: AI for SC small businesses](learn/primer-05-small-business.html)
  - [One Useful Thing (Ethan Mollick)](https://www.oneusefulthing.org/)
  - Co-Intelligence (Ethan Mollick, 2024)
- Practitioner
  - [Anthropic Academy](https://academy.claude.com/) (Includes the AI Fluency course)
  - [Learn Prompting](https://learnprompting.org/)
  - [Simon Willison's Weblog](https://simonwillison.net/) (Practical, skeptical, current)
- Builder
  - [Claude prompt engineering guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview)
  - [OpenAI prompt engineering guide](https://developers.openai.com/api/docs/guides/prompt-engineering)

## 4. Building with AI

Building covers how working AI applications are put together, from a single API call to multi-step agents. The SCAIO Policy Navigator, a retrieval tool over SC policy documents, is a local worked example.

### Subtopics

- APIs and models
  - Calling a model through an API
  - Choosing a model: cost, speed, quality
  - Running open models locally
- Retrieval (RAG)
  - Embeddings and vector databases
  - Chunking and indexing documents
  - Grounding answers in sources
- Tools and agents
  - Tool use and function calling
  - Agent loops and workflows
  - Model Context Protocol (MCP) and connectors
  - Coding agents
- Fine-tuning
  - When to fine-tune vs. prompt vs. retrieve
  - Small models and distillation
- Evaluation and operations
  - Writing evals and test sets
  - Monitoring, logging, and cost control
  - Deployment and reliability

### Where to learn

- Curious
  - [Building Effective Agents (Anthropic)](https://www.anthropic.com/engineering/building-effective-agents) (Plain-language overview of agent patterns)
  - [Pinecone Learn](https://www.pinecone.io/learn/) (Explainers on embeddings and retrieval)
- Practitioner
  - [DeepLearning.AI short courses](https://www.deeplearning.ai/courses) (One- to two-hour courses on RAG, agents, evals)
  - [Hugging Face Agents Course](https://huggingface.co/learn/agents-course)
  - [Model Context Protocol](https://modelcontextprotocol.io/) (Spec and tutorials)
- Builder
  - [Claude developer docs](https://platform.claude.com/docs/en/home)
  - [AI Engineering (Chip Huyen, 2025) and her blog](https://huyenchip.com/) (The blog is free)
  - [Hamel Husain on evals](https://hamel.dev/)
  - [Retrieval-Augmented Generation (Lewis et al., 2020)](https://arxiv.org/abs/2005.11401) (The original RAG paper)
  - [Ollama](https://ollama.com/) (Run open models locally)

## 5. Infrastructure

Infrastructure is the physical side of AI: chips, data centers, power, and water. It is the branch where South Carolina is most directly involved, through data-center investment and utility planning.

### Subtopics

- Compute
  - GPUs and AI accelerators
  - Why training and inference need different hardware
  - Compute as a measure of AI progress
- The chip supply chain
  - Design (Nvidia, AMD), fabrication (TSMC), and lithography tools (ASML)
  - Export controls and geopolitics
  - Domestic manufacturing efforts
- Data centers
  - Hyperscale vs. colocation facilities
  - Siting decisions and local incentives
  - Cloud providers and capacity
- Energy and water
  - Electricity demand and grid planning
  - Generation sources: gas, nuclear, renewables
  - Cooling and water use
  - Who pays: rate design and large-load tariffs
- SC layer
  - Data-center investment across the state
  - Utility planning and rate pilots

### Where to learn

- Curious
  - [SCAIO Journal: South Carolina's Data-Center Decade](scaio-article-data-center-decade.html)
  - [SCAIO primer: AI for SC county council members](learn/primer-county-council.html)
  - Chip War (Chris Miller, 2022)
- Practitioner
  - [Energy and AI (International Energy Agency)](https://www.iea.org/reports/energy-and-ai)
  - [Epoch AI](https://epoch.ai/) (Data on compute, training runs, and trends)
  - [Asianometry](https://www.youtube.com/@Asianometry) (Semiconductor industry)
  - [Acquired](https://www.acquired.fm/) (Episodes on Nvidia and TSMC)
- Builder
  - [SemiAnalysis](https://semianalysis.com/) (Deep industry analysis, partly paywalled)
  - [2024 United States Data Center Energy Usage Report (Lawrence Berkeley National Laboratory)](https://eta.lbl.gov/publications/2024-lbnl-data-center-energy-usage-report)

## 6. Policy and governance

This branch tracks how governments, standards bodies, and institutions are responding to AI, from federal frameworks down to a county procurement contract.

### Subtopics

- Core vocabulary
  - Safety vs. alignment vs. governance vs. regulation
  - Risk-based approaches to regulation
- Federal (U.S.)
  - Executive actions and national AI plans
  - NIST standards and the AI Risk Management Framework
  - Federal preemption and the state-law debate
- States
  - State AI legislation trends: deepfakes, education, health, government use
  - Comparing state approaches
- International
  - EU AI Act
  - OECD principles and global coordination
  - China's and the UK's approaches
- Government use of AI
  - Procurement standards and contract terms
  - Agency use-case inventories and review processes
- Specific policy areas
  - Copyright and training data
  - Privacy and data protection
  - Liability and accountability
- SC layer
  - SC AI Strategy and the State AI Center of Excellence
  - SC General Assembly AI legislation and the Senate Special Committee on AI

### Where to learn

- Curious
  - [SCAIO primer: Safety, alignment, governance, regulation](learn/primer-safety-vocabulary.html)
  - [SCAIO primer: A legislator's AI glossary](learn/primer-09-legislator-glossary.html)
  - [SCAIO Journal: Everywhere at Once](scaio-article-everywhere-at-once.html)
- Practitioner
  - [SCAIO Policy Tracker](policy/)
  - [SCAIO primer: AI procurement for SC government](learn/primer-03-procurement.html)
  - [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
  - [AI Index (Stanford HAI)](https://hai.stanford.edu/ai-index) (Annual report with a policy chapter)
  - [NCSL AI legislation tracker](https://www.ncsl.org/technology-and-communication/artificial-intelligence-2025-legislation) (2025 session; NCSL had not posted a 2026 page as of Oct 2026)
- Builder
  - [EU AI Act explorer](https://artificialintelligenceact.eu/)
  - [OECD.AI Policy Observatory](https://oecd.ai/)
  - [Center for Security and Emerging Technology (Georgetown)](https://cset.georgetown.edu/)
  - [Centre for the Governance of AI](https://www.governance.ai/)
  - [U.S. Copyright Office: Copyright and AI](https://www.copyright.gov/ai/)

## 7. Safety and security

Safety and security covers what can go wrong with AI and the work to prevent it. The branch follows SCAIO's map of risk by source: misuse, malfunction, and systemic effects.

### Subtopics

- Mapping risk
  - Misuse, malfunction, and systemic risk
  - Near-term vs. long-term concerns
  - Incident tracking
- Security of AI systems
  - Prompt injection and jailbreaks
  - Data poisoning and model theft
  - Securing agents and connected tools
- AI as a security threat
  - AI-assisted phishing and voice cloning
  - Ransomware and attacks on public institutions
- Alignment
  - What alignment research measures
  - Evaluations, red-teaming, and model testing
  - Interpretability as a safety tool
- Frontier safety
  - Lab safety frameworks and scaling policies
  - Government AI safety and standards institutes
  - International safety assessments

### Where to learn

- Curious
  - [SCAIO Journal: A Plain-Language Map of AI Risk](scaio-article-map-of-ai-risk.html)
  - [SCAIO Journal: Between Doom and Denial](scaio-article-between-doom-and-denial.html)
  - [SCAIO primer: What alignment research actually is](learn/primer-alignment-research.html)
  - [Robert Miles AI Safety](https://www.youtube.com/@RobertMilesAI)
- Practitioner
  - [SCAIO Journal: AI, cybersecurity, and public risk in the Palmetto State](scaio-article-cybersecurity.html)
  - [SCAIO primer: AI for SC local government](learn/primer-08-local-gov.html)
  - [AI Incident Database](https://incidentdatabase.ai/)
  - [MIT AI Risk Repository](https://airisk.mit.edu/)
  - [International AI Safety Report](https://internationalaisafetyreport.org/)
- Builder
  - [OWASP Gen AI Security Project](https://genai.owasp.org/) (Top 10 for LLM applications)
  - [MITRE ATLAS](https://atlas.mitre.org/) (Adversarial threat framework for AI)
  - [Introduction to AI Safety, Ethics, and Society (Center for AI Safety)](https://www.aisafetybook.com/) (Free textbook)
  - [BlueDot Impact](https://bluedot.org/) (Free cohort courses on AI safety and governance)

## 8. AI and society

This branch covers how AI is changing specific parts of life and the economy. Most existing SCAIO primers live here, since each one addresses a sector.

### Subtopics

- Work and the economy
  - Task exposure vs. actual adoption
  - Productivity effects
  - Retraining and workforce programs
- Education
  - AI in classrooms and homework
  - District policies and procurement
  - AI literacy as a subject
- Health care
  - Clinical AI and diagnostics
  - Insurance claims and prior authorization
  - Rural vs. large-system access
- Manufacturing and industry
  - Predictive maintenance and quality control
  - Robotics and humanoid pilots
- Media and information
  - Deepfakes and voice cloning
  - Content provenance and labeling
  - Elections and misinformation
- Fairness and rights
  - Bias in automated decisions
  - Transparency and the right to explanation
- Creative work
  - Copyright and artists
  - AI-assisted creative tools

### Where to learn

- Curious
  - [SCAIO primer: AI in SC schools](learn/primer-02-schools.html)
  - [SCAIO primer: Healthcare AI in SC](learn/primer-06-healthcare.html)
  - [SCAIO primer: AI in SC manufacturing](learn/primer-07-manufacturing.html)
  - [SCAIO primer: Spotting synthetic media](learn/primer-04-synthetic-media.html)
  - AI Snake Oil (Arvind Narayanan and Sayash Kapoor, 2024)
- Practitioner
  - [SCAIO Journal: What We Know and Don't About AI's Effect on SC Workers](scaio-article-workforce-what-we-know.html)
  - [SCAIO Journal: What AI means for SC manufacturing](scaio-article-manufacturing.html)
  - [Anthropic Economic Index](https://www.anthropic.com/economic-index) (How AI is used at work)
  - [TeachAI](https://www.teachai.org/) (AI guidance for schools)
  - [C2PA](https://c2pa.org/) (Content provenance standard)
- Builder
  - [Brookings: Artificial Intelligence](https://www.brookings.edu/topics/artificial-intelligence/)
  - Weapons of Math Destruction (Cathy O'Neil, 2016)

## 9. The players

The players branch maps who builds and shapes AI, grouped by where each sits in the stack. It doubles as the outline for the SCAIO Who's Who.

### Subtopics

- Frontier labs
  - OpenAI, Anthropic, Google DeepMind, Meta, xAI
  - Mistral (France), DeepSeek and Alibaba Qwen (China)
- Chips and hardware
  - Nvidia, AMD, Intel, Broadcom
  - TSMC (fabrication), ASML (lithography)
- Cloud and compute
  - Amazon Web Services, Microsoft Azure, Google Cloud, Oracle
  - Specialized AI clouds such as CoreWeave
- Platforms and open source
  - Hugging Face (model and dataset hub)
  - GitHub, Ollama, open-weight model communities
- Applications
  - AI search, coding tools, and creative tools
  - AI features inside existing software
- Research and nonprofits
  - Allen Institute for AI (Ai2), EleutherAI
  - University institutes such as Stanford HAI
- Government bodies
  - NIST and the Center for AI Standards and Innovation
  - UK AI Security Institute
  - EU AI Office
- SC layer
  - USC AI Institute, Clemson School of Computing, SCRA, ADAPT in SC, SC State Government AI Center of Excellence, Charleston Digital Corridor

### Where to learn

- Curious
  - [SCAIO primer: The South Carolina AI landscape](learn/primer-10-sc-landscape.html)
  - SCAIO Who's Who in AI (planned)
- Practitioner
  - [AI Index (Stanford HAI)](https://hai.stanford.edu/ai-index) (Who produces notable models)
  - [Epoch AI](https://epoch.ai/) (Database of notable models and their developers)
  - [LMArena](https://lmarena.ai/) (Crowd-sourced model rankings)
  - [Artificial Analysis](https://artificialanalysis.ai/) (Model and provider benchmarks)
- Builder
  - [Hugging Face Hub](https://huggingface.co/models) (Browse open models and their makers)
  - Company model cards and system cards (One for each major release)

## Staying current

- Newsletters
  - [The Batch (DeepLearning.AI)](https://www.deeplearning.ai/the-batch/) (Weekly, general audience)
  - [Import AI (Jack Clark)](https://jack-clark.net/) (Weekly, research and policy)
  - [One Useful Thing (Ethan Mollick)](https://www.oneusefulthing.org/) (Practical use)
  - [Interconnects (Nathan Lambert)](https://www.interconnects.ai/) (Models and training)
  - [Simon Willison's Weblog](https://simonwillison.net/) (Tools and security)
- Podcasts
  - [Hard Fork (New York Times)](https://www.nytimes.com/column/hard-fork) (General audience)
  - [Latent Space](https://www.latent.space/) (AI engineering)
  - [Dwarkesh Podcast](https://www.dwarkesh.com/) (Long interviews with researchers)
- YouTube
  - [Two Minute Papers](https://www.youtube.com/@TwoMinutePapers) (Research highlights)
  - [AI Explained](https://www.youtube.com/@aiexplained-official) (Model releases and benchmarks)
- South Carolina
  - [SCAIO Journal](index.html#journal)
  - [SCAIO Policy Tracker](policy/)
  - [The Artificial Intelligence Landscape of South Carolina](report/index.html) (SCAIO flagship report)
