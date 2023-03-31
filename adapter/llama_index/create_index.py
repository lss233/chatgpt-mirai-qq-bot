from llama_index import (
    GPTKeywordTableIndex,
    SimpleDirectoryReader,
    LLMPredictor,
    ServiceContext,
    GPTTreeIndex,
    GPTSimpleVectorIndex, 
    GithubRepositoryReader
)
from langchain import OpenAI
import os
import nest_asyncio

# load from directory
#documents = SimpleDirectoryReader('./data').load_data() # 随地大小便
#llm_predictor = LLMPredictor(llm=OpenAI(temperature=0.7, model_name="gpt-4", max_tokens=4000))
#service_context = ServiceContext.from_defaults(llm_predictor=llm_predictor)
#index = GPTKeywordTableIndex.from_documents(documents, service_context=service_context)
#index = GPTTreeIndex.from_documents(documents, service_context=service_context)
#index.save_to_disk('./index.json')

# load from github
nest_asyncio.apply()
github_token = os.environ['GITHUB_TOKEN']
owner = "lss233"
repo = "chatgpt-mirai-qq-bot"
branch = "browser-version"

documents = GithubRepositoryReader(
    github_token=github_token,
    owner=owner,
    repo=repo,
    use_parser=False,
    verbose=False,
).load_data(branch=branch)
index = GPTSimpleVectorIndex.from_documents(documents)
index.save_to_disk("github_index.json")