from sentence_transformers import SentenceTransformer,util
import chromadb
import requests

# all-MiniLM-L6-v2 for text to vectors
embedding_model=SentenceTransformer("all-MiniLM-L6-v2")

#testing cos similarities
# print("TESTING COSINE SIMILARITIES:")
# sentence_a="A loan for farmers"
# sentence_b="Financial help for agricultural workers"
# sentence_c="Football world cup"

# vector_a=embedding_model.encode(sentence_a)
# vector_b=embedding_model.encode(sentence_b)
# vector_c=embedding_model.encode(sentence_c)

# similarity_ab=util.cos_sim(vector_a,vector_b)
# similarity_ac=util.cos_sim(vector_a,vector_c)
# similarity_bc=util.cos_sim(vector_b,vector_c)

# print("similarity between farmer sentences:",round(float(similarity_ab),3))
# print("similarity between 1st farmer sentence and random:",round(float(similarity_ac),3))
# print("similarity between 2nd farmer sentence and random:",round(float(similarity_bc),3))

# print("CHECK DONE")

## TESTING COSINE SIMILARITIES:
## similarity between farmer sentences: 0.67
## similarity between 1st farmer sentence and random: 0.056
## similarity between 2nd farmer sentence and random: -0.023
## CHECK DONE


def ask_llm(user_question,parts):
    context=""
    for part in parts:
        context=context+"- "+part+"\n"

    prompt="Use only the following information to answer the question. If the answer is not in the context, say you don't know.\n\nContext:\n" + context + "\nQuestion: " + user_question
    response=requests.post("http://localhost:11434/api/chat",json={
        "model": "qwen2.5:3b",
        "messages": [{"role": "user","content": prompt}],
        "stream": False
    })
    result=response.json()
    answer=result["message"]["content"]
    return answer

#note: CHROMA USES DISTANCE, NOT COSINE SIMILARITIES SO SMALLER IS MORE SIMILAR
#TAKES A QUERT, COMPARES AND SEARCHES THEN RETURNS DISTANCE (0-2)
chroma_client=chromadb.Client()
loans_collection=chroma_client.create_collection("abhi_loans")

text_file=open("testknowledge.txt","r")
raw_text=text_file.read()
text_file.close()

parts=raw_text.strip().split("\n")
all_embeddings=[]
for part in parts:
    embedding=embedding_model.encode(part)
    all_embeddings.append(embedding.tolist())

all_ids=[]
for i in range(0,len(parts)):
    all_ids.append("part_"+str(i))

loans_collection.add(documents=parts,embeddings=all_embeddings,ids=all_ids)  # original text, vector representations,unique ids
print("stored",len(parts),"parts in chromadb")

#testing
user_query="does abhi offer any loans for females"
query_embedding=embedding_model.encode(user_query).tolist()
results=loans_collection.query(query_embeddings=[query_embedding],n_results=3)

answer=ask_llm(user_query,results["documents"][0])
print("ANSWER:",answer)

# user_query2="are there any loans for laptop?"
# query_embedding2=embedding_model.encode(user_query2).tolist()
# results2=loans_collection.query(query_embeddings=[query_embedding2],n_results=1)

# print("QUERY:",user_query)
# top_document=results["documents"][0][0]
# top_distance=results["distances"][0][0]
# print("best match:",top_document)
# print("distance:",round(top_distance,3))

# print("\nQUERY:",user_query2)
# top_document2=results2["documents"][0][0]
# top_distance2=results2["distances"][0][0]
# print("best match:",top_document2)
# print("distance:",round(top_distance2,3))

# QUERY: what loans offered by abhi for farmers?
# best match: Kashtkar Karza: A loan that meets a farmer's financial needs to support expansion of their farming business.
# distance: 0.74

# QUERY: are there any loans for laptop?
# best match: ABHI Microfinance offers multiple loan products with competitive interest rates, easy repayment options, and quick processing.
# distance: 1.228