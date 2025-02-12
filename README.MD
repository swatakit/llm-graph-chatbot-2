# Setup


## 1. Install ollama and pull models

[Download Ollama](https://ollama.com/)

models: 

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```


## 2. Setup python env
```bash
conda create --name langgraph-aml python=3.12.4 -y
activate langgraph-aml
pip install -r requirements.txt
```

Then install the latest langchain community/experimental and other packages
```bash
pip install langchain_community
pip install langchain-experimental
pip install langchain_anthropic
pip install langchain_neo4j
pip install graphviz
pip install neo4j

```

## 3. Install pytorch [Highly Recommended]

[Install Pytorch](https://pytorch.org/get-started/locally/)