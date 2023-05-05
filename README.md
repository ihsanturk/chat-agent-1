# Infinite Memory Chatbot

Infinite Memory Chatbot is a Python-based chatbot leveraging OpenAI's GPT-4 language model and the Pinecone vector database to create a conversation bot that remembers past interactions and uses this information to generate more relevant and informed responses.

## Requirements

- Python 3.8 or later
- Packages: os, typing, datetime, pickle, json, pinecone, time, uuid, sqlite3, selenium, and openai

Make sure to install the required packages using pip:

```bash
pip install -r requirements.txt
```

## Setup

1. Sign up for a Pinecone account and obtain your API key.
2. Sign up for an OpenAI account and obtain your API key.
3. Create a new project in your Google Cloud Console, create an Oauth key. Give it access to 'https://www.googleapis.com/auth/gmail.modify' and 'https://www.googleapis.com/auth/calendar.events' scopes.
4. Download the Oauth json, and place it in this project's directory. RENAME IT TO `credentials.json`.
5. From your Google Cloud Console, enable the Gmail and Calendar APIs.
6. At the top of `aei.py`, set your email SENDER field and gmail address.
7. At the top of `chat.py`, set your API keys.
8. IF YOU DO NOT HAVE GPT-4 ACCESS: set the GPT model to 'gpt-3.5-turbo' at the top of `chat.py`. Expect subpar performance.

## Usage

Run the `chat.py` from this project's directory:

```bash
python chat.py
```

The chatbot will start, and you can type your messages to interact with it. To exit the chatbot normally, type `/q/`. To exit without upserting embedded chats from current session to Pinecone, perform an anomalous exit via Ctrl+C.

The chatbot supports various special instructions from the user:

- `/q/`: Upsert the current session to Pinecone and quit chat.
- `/m/`: Select a different GPT model.
- `/e/`: Execute the next line as a Python command.
- `/max/`: Set the maximum response tokens for GPT.
- `/temp/`: Set the GPT temperature.
- `/freq/`: Set the GPT frequency penalty.
- `/sl/`: Set the maximum number of characters to read from Google results when using the search AEI.
- `/top_k/`: Set the number of vectors to return in Pinecone query.

In addition to chat responses, the assistant has the ability to call AEIs (Agent Extesion Interfaces) to perform a limited number of tasks. Currently, these are 1) perform a Google search and read the beginning of the first results page, 2) send an email through the Gmail API, 3) view Gmail calendar events, and 4) create Gmail calendar events.

## Additional Parameter Adjustments

- Most GPT prompt arguments have been parametrized, so you can change them at the top of `chat.py`.
- To set the maximum number of messages to return for each Long-Term Memory (LTM) qury from Pinecone, set `top_k`, located at the top of `chat.py`.
- To set how many characters to read from the Google results page during a Google query, change `searchLength`, located at the top of `chat.py`.
- To alter the main alignment prompt, edit `alignmentPrompt.txt`.

## Alignment

Most of the application-specific alignment is accomplished through the `alignmentPrompt`. We opted to include speaker and timestamp in stored messages so that GPT could see this information. However, this presented the challenge of stopping it from generating a speaker and timestamp in its responses. In addition to repeatedly telling it not to include these things, we also added a {'role':'assistant', 'content':'ASSISTANT at '+timestring+': '} message to the end of the completion prompt to "trick" it into "thinking" that it had already generated the speaker and timestamp.

## Agent Extension Interfaces (AEIs)

We introduce AEIs as a rudimentary framework for augmenting the capabilities of a generative transformer by providing a sanitized and type-safe interface between agent output and external services or programs. We include specific instructions in the alignment prompt on how the assistant can access these interfaces, and implement a routine that identifies which responses are chats and which are AEI calls. AEI calls are then parsed, and the extracted arguments are passed to the appropriate AEI. This approach ensures that there is no way for the agent to perform, call, or execute anything outside of the abilities explicitly afforded by the AEIs. In addition, the AEI asks for user approval before sending an assistant-generated email.

## License

This project is licensed under the GNU Affero General Public License (AGPLv3). You can find the full text of the AGPLv3 license at the following link: https://www.gnu.org/licenses/agpl-3.0.en.html.
