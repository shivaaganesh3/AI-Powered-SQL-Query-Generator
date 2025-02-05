import os
import streamlit as st
import pickle
import time
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import UnstructuredURLLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings,ChatGoogleGenerativeAI
from langchain.vectorstores import FAISS
from dotenv import load_dotenv
load_dotenv()

st.title("EQUITY - NEWS Research Tool")

st.sidebar.title("News Article URLs")

urls=[]
for i in range(2):
    url=st.sidebar.text_input(f"URL {i+1}")
    urls.append(url)

process_url_clicked=st.button("Analyze")
file_path="faiss_store_gemini.pkl"


main_placeholder=st.empty()
if process_url_clicked:
    loader=UnstructuredURLLoader(urls)
    main_placeholder.write("Data Loading Started....")
    data=loader.load()

    text_splitter=RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ". ", "!", "?", ";", ":", "\t", " "],
        chunk_size=500
    )
    main_placeholder.write("Text Splitter Started....")
    docs=text_splitter.split_documents(data)

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vectorindex_gemini = FAISS.from_documents(docs, embedding=embeddings)
    main_placeholder.write("Embeddings Vector Build Started....")
    time.sleep(2)

    vectorindex_gemini.save_local("faiss_store_index")
    main_placeholder.write("Embeddings Vector Build Completed....")


llm = ChatGoogleGenerativeAI(
    model="gemini-1.0-pro",
    temperature=0,
    max_tokens=500,
    timeout=None,
    max_retries=10,
)

embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
query=main_placeholder.text_input("Enter your query here:")
if query:
    if os.path.exists("faiss_store_index"):
        vectorindex_gemini = FAISS.load_local("faiss_store_index", embeddings, allow_dangerous_deserialization=True)
        chain=RetrievalQAWithSourcesChain.from_llm(llm=llm,retriever=vectorindex_gemini.as_retriever())
        try:
            result=chain({"question":query},return_only_outputs=True)
            st.header("Results")
            st.subheader(result["answer"])

            sources=result.get("sources","")
            if sources:
                st.subheader("Sources")
                sources_list=sources.split("\n")
                for source in sources_list:
                    st.write(source)
        except Exception as e:
            st.error("An error occurred while retrieving the results. This may be due to exhaustion of the API limits. Please try again later.")
    else:
        st.error("Embeddings Vector file not found. Please run the data loading and vector build process first.")
