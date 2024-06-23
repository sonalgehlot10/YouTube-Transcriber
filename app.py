import streamlit as st
from dotenv import load_dotenv
import os
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from keybert import KeyBERT
import re
import random

load_dotenv()  # Load all the environment variables

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize the KeyBERT model
kw_model = KeyBERT()

prompt = """
You are a YouTube video summarizer. You will be taking the transcript text
and summarizing the entire video and providing the important summary in points
within 250 words. Please provide the summary of the text given here:
"""

def extract_transcript_details(youtube_video_url):
    try:
        video_id = youtube_video_url.split("=")[1]
        transcript_text = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = " ".join([i["text"] for i in transcript_text])
        return transcript
    except Exception as e:
        raise e

def generate_gemini_content(transcript_text, prompt, level):
    model = genai.GenerativeModel("gemini-pro")
    
    if level == "Brief":
        # Use the first 150 words of the transcript for a brief summary
        input_text = prompt + " ".join(transcript_text.split()[:150])
    elif level == "Detailed":
        # Use the entire transcript for a more detailed summary
        input_text = prompt + transcript_text
    else:
        raise ValueError("Invalid level selected")
    
    response = model.generate_content(input_text)
    return response.text


def extract_keywords(text):
    keywords = kw_model.extract_keywords(text, keyphrase_ngram_range=(1, 2), stop_words='english')
    return [kw[0] for kw in keywords]

def generate_quiz(summary, keywords):
    quiz_questions = []
    sentences = summary.split('.')
    for sentence in sentences:
        for keyword in keywords:
            keyword_lower = keyword.lower()
            sentence_lower = sentence.lower()
            # Use regex to ensure we're matching whole words
            regex_pattern = r'\b' + re.escape(keyword_lower) + r'\b'
            if re.search(regex_pattern, sentence_lower):
                question = re.sub(regex_pattern, '_____', sentence, flags=re.IGNORECASE).strip() + "."
                # Generate multiple-choice options
                options = [keyword]  # Include the correct keyword as one of the options
                while len(options) < 4:  # Generate 3 incorrect options
                    random_keyword = random.choice(keywords)
                    if random_keyword not in options:
                        options.append(random_keyword)
                random.shuffle(options)  # Shuffle options to randomize the order
                quiz_questions.append({
                    "question": question,
                    "options": options,
                    "answer": keyword
                })
                break  # Move to the next sentence after finding the first keyword match
    return quiz_questions[:5]  # Limit to 5 questions

st.title("YouTube Transcript to Detailed Notes Converter")
youtube_link = st.text_input("Enter YouTube Video Link:")

summary_levels = ["Brief", "Detailed"]
selected_level = st.selectbox("Select Summary Level:", summary_levels)

if youtube_link:
    video_id = youtube_link.split("=")[1]
    st.image(f"http://img.youtube.com/vi/{video_id}/0.jpg", use_column_width=True)

if st.button("Get Detailed Notes"):
    transcript_text = extract_transcript_details(youtube_link)

    if transcript_text:
        summary = generate_gemini_content(transcript_text, prompt, selected_level)
        st.markdown(f"## {selected_level} Notes:")
        st.write(summary)
        
        # Generate and display keywords
        keywords = extract_keywords(summary)
        
        # Generate and display quiz with multiple-choice options
        quiz_questions = generate_quiz(summary, keywords)
        st.markdown("## Quiz Questions:")
        if quiz_questions:
            for i, question_data in enumerate(quiz_questions):
                question = question_data['question']
                options = question_data['options']
                answer = question_data['answer']
                
                st.markdown(f"**Q{i+1}:** {question}")
                
                # Display multiple-choice options
                option_letters = ['A', 'B', 'C', 'D']
                for j, option in enumerate(options):
                    st.write(f"{option_letters[j]}. {option}")
                
                st.markdown(f"Correct Answer: {answer}")
                st.markdown("---")
        else:
            st.write("No quiz questions generated.")
