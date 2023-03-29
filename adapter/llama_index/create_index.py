from llama_index import (
    GPTKeywordTableIndex,
    SimpleDirectoryReader,
    LLMPredictor,
    ServiceContext,
    GPTTreeIndex
)
from langchain import OpenAI
import os

os.environ['OPENAI_API_KEY'] = "xxx"
documents = SimpleDirectoryReader('./data').load_data() # 随地大小便
llm_predictor = LLMPredictor(llm=OpenAI(temperature=0.7, model_name="gpt-4", max_tokens=4000))
service_context = ServiceContext.from_defaults(llm_predictor=llm_predictor)
#index = GPTKeywordTableIndex.from_documents(documents, service_context=service_context)
index = GPTTreeIndex.from_documents(documents, service_context=service_context)
index.save_to_disk('./index.json')