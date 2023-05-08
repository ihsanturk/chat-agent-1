#!/usr/bin/env python
# coding: utf-8

# Infinite Memory Chatbot V 1.0
# 2023-05-02/

# idea: try including some recent messages in vector search to handle follow up questions that require context

# Get the agent extension interfaces
from aei import *

import os
from typing import List, Tuple
from datetime import datetime
import pickle
import json
import pinecone
import time
from uuid import uuid4

from sqlite3 import connect

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

import openai

# make sure to set your API keys
pinecone_key = 'YOUR PINECONE API KEY'
openai.api_key = "YOUR OPENAI API KEY"

# GPT API args
model='gpt-4' # 'gpt-3.5-turbo' also works
max_tokens=512
temperature=0.0
top_p=1.0
freq_p=0.0
pres_p=0.0

# Pinecone vector query limit
top_k = 20

# how many characters to read from Google results page when search AEI is called
searchLength = 1000

with open('alignmentPrompt.txt', 'r') as f:
    # read the alignment prompt file

    alignmentPrompt = eval(f.read())

def getElementText(element):
    # recursively extracts all text content from an HTML element and its children
    # takes: selenium driver element
    # returns: string

    text = element.text.strip()
    for child in element.find_elements('xpath','./*'):
        text += '\n' + getElementText(child).strip()
        if len(text) >= searchLength:
            return text[:searchLength+1]
    return text[:searchLength+1]

def chatComplete(messages, model=model, max_tokens=max_tokens, temperature=temperature, top_p=top_p, freq_p=freq_p, pres_p=pres_p):
    # call openAI API and generate response
    # takes: list of message dicts, string, int, float, float, float, float, float
    # returns: chat completion object

    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        frequency_penalty=freq_p,
        presence_penalty=pres_p
    )
    return response

def embedAda(text):
    # generate text embedding
    # takes: string
    # returns: embedding vector with 1536 dimensions

    text = text.encode(encoding='ASCII', errors='ignore').decode()
    response = openai.Embedding.create(input=text, engine='text-embedding-ada-002')
    # create vector list
    vector = response['data'][0]['embedding']
    return vector

def getRecentChat():
    # not implemented or used. ignore

    conn = connect('chat.db')
    cur = conn.cursor()
    cur.execute('')

def loadRes(results):
    # load indexed chats from LTM database based on Pinecone vector query
    # takes: results list from Pinecone vector query
    # returns: list containing a conversation snippet with any relevant results and some guiding system messages

    conn = connect('chat.db')
    cur = conn.cursor()
    out = []
    for match in results['matches']:
        # print(match['id'])
        cur.execute('SELECT * FROM ChatHistory WHERE id = ?', (match['id'],))
        msg = cur.fetchone()
        if msg:
            out.append(msg)

    if out:
        # for m in out:
        #     print(m)
        outblock = '\n\n'.join([m[1] for m in out if m])
        outfinal = [{'role':'system', 'content': 'These are the most semantically similar past messages to the newest user message: ' + '\n\n' + outblock + '\n\n'},{'role':'system', 'content': 'REMEMBER NOT TO INCLUDE "ASSISTANT" OR THE TIMESTAMP AT THE BEGINNING OF YOUR RESPONSE.\n\n'}]
        # print(outfinal)
        return outfinal
    else:
        return [{'role':'system', 'content': 'REMEMBER NOT TO INCLUDE "ASSISTANT" OR THE TIMESTAMP AT THE BEGINNING OF YOUR RESPONSE. ONLY INCLUDE YOUR ACTUAL RESPONSE!!!\n\n'}]

def calParse(text):
    # parse calendar AEI commands
    # takes: string formatted as a calendar AEI command beginning with an action
    # returns: a dict of args:values extracted from AEI command

    print('\n',text)
    code = text
    parsed = {'action':None, 'start':None, 'end':None, 'max':10, 'loc':None, 'name':'Autogenerated Event', 'description':'This even was autogenerated by AI.', 'eventid': None}
    parsing = True

    actionSplit = code.split('/;', maxsplit=1)[-1].split(';/', maxsplit=1)
    parsed['action'] = actionSplit[0].lower()

    code = actionSplit[-1].split('/;', maxsplit=1)[-1]

    while parsing:

        firstSplit = code.split(';/', maxsplit=1)
        if len(firstSplit) == 1:
            parsing = False
            break

        first = firstSplit[0].lower()
        secondSplit = firstSplit[-1].split('/;', maxsplit=1)
        second = secondSplit[0]
        parsed[str(first)]=str(second)

        code = secondSplit[-1]

    print('\nParsed calendar command: ',parsed)
    return parsed

def makePostPrompt():
    # make a snippet for the end of the completion prompt that contains an assistant 
    # message with a speaker and  dummy timestamp tag, so that the LLM 'believes' it has
    # already generated this, and omits it from the actual response
    # takes: No args
    # returns: list containing conversation snippet

    timestamp = time.time()
    timestring = str(datetime.fromtimestamp(timestamp))
    postPrompt = [{'role':'assistant', 'content':'ASSISTANT at '+timestring+': '}]
    return postPrompt


if __name__ == '__main__':

    # start Pinecone service
    pinecone.init(api_key=pinecone_key, environment='us-west1-gcp-free')
    vecdb = pinecone.Index('chat-test-1')

    # initialize conversation lists
    ids = [] # stores chat/vector IDs
    currentConvo = [] # conversation snippet containing entire session
    currentText = [] # same as currentConvo, but with timestamps removed for embedding

    while True:
        # main loop

        userIn = input('\nYOU: ')

        # check for special instructions from user
        if userIn == '/q/':
            # upsert current session to Pinecone then quit chat
            # entire session is upserted only upon nominal exit for efficiency, to avoid recalling recent messages in semantic search, and to enable the current session to be easily discarded unsaved

            print('\nUpserting current conversation...')

            for i in range(len(ids)):
                identifier = ids[i]
                chat = currentText[i] # upserted records do not include timestamp and speaker
                vector = embedAda(chat)
                payload = []
                payload.append((identifier, vector))
                vecdb.upsert(payload)
            print('Done')
            exit()

        elif userIn == '/m/':
            # select GPT model. refer to openAI documentation for acceptable values

            model = input('\nSelect GPT Model: ')
            print('Done. model = '+str(model))

        elif userIn == '/e/':
            # execute next user input as python

            try:
                exec(input('\nPYTHON EXECUTE: '))
                print('Done')
            except:
                print('Error occurred in execution.')

        elif userIn == '/max/':
            # set max GPT response tokens

            try:
                max_tokens = int(input('\nSet max response tokens: '))
                print('Done')
            except:
                print('Error: max_tokens must be an int.')

        elif userIn == '/temp/':
            # set GPT temperature

            try:
                temperature=float(input('\nSet temperature: '))
                print('Done')
            except:
                print('Error: temperature must be an int.')

        elif userIn == '/freq/':
            # set GPT frequency penalty

            try:
                freq_p=float(input('\nSet frequency penalty: '))
                print('Done')
            except:
                print('Error: freq_p must be an int.')

        elif userIn == '/sl/':
            # set max number of characters to read in Google AEI call

            try:
                searchLength = int(input('\nSet search page text max length: '))
                print('Done')
            except:
                print('Error')

        elif userIn == '/top_k/':
            # set number of vectors to return in Pinecone query

            try:
                top_k = int(input('\nSet top_k: '))
                print('Done. top_k = '+str(top_k))
            except:
                print('Error')

        elif userIn == '/d/':
            try:
                currentText.pop()
                print(f'Deleted most recent message: ', currentConvo.pop())
            except:
                print('Error: could not delete recent message.')

        else:
            # store user input to LTM database

            timestamp = time.time()
            timestring = str(datetime.fromtimestamp(timestamp))
            message = 'USER at '+timestring+': '+userIn

            currentConvo.append({'role':'user', 'content':message})
            currentText.append(userIn)

            identifier = str(uuid4())
            ids.append(identifier)

            conn = connect('chat.db')
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS ChatHistory (
                    id TEXT,
                    message TEXT,
                    speaker TEXT,
                    timestamp TEXT,
                    timestring TEXT
                )
            ''')
            cur.execute('INSERT INTO ChatHistory (id, message, speaker, timestamp, timestring) VALUES (?, ?, ?, ?, ?)', (identifier, message, 'USER', timestamp, timestring))
            conn.commit()

            # embed user message and query Pinecone for relevant LTM data
            if len(currentText) >= 4:
                vector = embedAda('\n\n'.join([item for item in currentText[-4:]]))
            else:
                vector = embedAda('\n\n'.join([item for item in currentText[-len(currentText):]]))

            results = vecdb.query(vector=vector, top_k=top_k, include_values=True, include_metadat=True)

            # create final GPT prompt
            conversation = alignmentPrompt + loadRes(results) + currentConvo + makePostPrompt()

            # create GPT chat completion
            chatResponse = chatComplete(conversation, model=model, max_tokens=max_tokens, temperature=temperature, top_p=top_p, freq_p=freq_p, pres_p=pres_p)
            responseText = chatResponse.choices[0].message.content

            # check for AEI call in GPT response by parsing response string
            responseCheck = responseText.split(';/', maxsplit=1)
            if responseCheck[0] == '/;GOOGSEARCH':
                # Google search AEI
                # agent passes a query string, then reads the first searchLength characters of text ripped from the first page of results

                print('\nASSISTANT Google Searched: '+responseCheck[1])
                
                # configure selenium
                chromeOptions = Options()
                chromeOptions.add_argument("--headless")

                # start a headless chrome browser and search Google
                driver = webdriver.Chrome(options=chromeOptions)
                driver.get("https://www.google.com")

                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "q")))

                searchBox = driver.find_element("name","q")
                searchBox.send_keys(responseCheck[1])
                searchBox.send_keys(Keys.RETURN)

                time.sleep(2)

                # find and consolidate page text
                htmlElement = driver.find_element('id','rcnt')
                pageText = getElementText(htmlElement)
                # print(str(pageText))
                driver.quit()

                timestamp = time.time()
                timestring = str(datetime.fromtimestamp(timestamp))

                # create conversation snippet with result page text
                searchResult = 'Here is the HTML of the results page of your Google search for "'+responseCheck[1]+'"" at '+timestring+'. You can read through it to infer information, then respond to the ChatUser: '+str(pageText)
                resultSnippet = [{'role':'system', 'content':searchResult}]


                # update completion prompt to include the search results
                conversation = alignmentPrompt + loadRes(results) + currentConvo + resultSnippet + makePostPrompt() # try oring current_convo with something to handle when its an empty list

                # create new response to user incorporating google search knowledge
                chatResponse = chatComplete(conversation, model=model, max_tokens=max_tokens, temperature=temperature, top_p=top_p, freq_p=freq_p, pres_p=pres_p)
                responseText = chatResponse.choices[0].message.content

            elif responseCheck[0] == '/;SENDMAIL':
                # Gmail AEI
                # agent passes formatted a string with arguments for recipient, subject, and content of email, which are then extracted and passed to Gmail API

                try:
                    # parse AEI command and extract args

                    mailRecipient = responseCheck[1].split(';/', maxsplit=1)[1].split('/;', maxsplit=1)
                    mailSubject = mailRecipient[1].split(';/', maxsplit=1)[1].split('/;', maxsplit=1)
                    mailContent = mailSubject[1].split(';/', maxsplit=1)[1].split('/;', maxsplit=1)


                    print('\nDraft email TO ',mailRecipient[0],', SUBJECT: ', mailSubject[0], ', CONTENT: ', mailContent[0])
                    if input('\nSend this email? Y to confirm, any other input to cancel: ') == 'Y':
                        sendMail(mailRecipient[0], mailSubject[0], mailContent[0])
                except:
                    print('Error parsing sendmail command.')

            elif responseCheck[0] == '/;CALENDAR':
                # Google calendar AEI
                # parse AEI command, extract args, call Google calendar API to view or create events

                # parse args
                args = calParse(responseCheck[1])

                # call AEI
                cal = calendar(action=args['action'], start=args['start'], end=args['end'], maxResults=args['max'], loc=args['loc'], name=args['name'], desc=args['description'], eventId=args['eventid'])

                # update completion prompt to include the search results
                calSnippet = [{'role':'system', 'content':cal}]
                currentConvo += calSnippet
                conversation = alignmentPrompt + loadRes(results) + currentConvo + makePostPrompt()
                #print(conversation)

                # create new response to user incorporating google search knowledge
                chatResponse = chatComplete(conversation, model=model, max_tokens=max_tokens, temperature=temperature, top_p=top_p, freq_p=freq_p, pres_p=pres_p)
                responseText = chatResponse.choices[0].message.content

            elif responseCheck[0] == '/;WTEXT':
                wtext = responseCheck[1].split('/;', maxsplit=1)[0]
                wfid = responseCheck[1].split(';/', maxsplit=1)[-1]
                wtext = wtxt(wtext, wfid)

                wtxtSnippet = [{'role':'system', 'content':wtext}]
                currentConvo += wtxtSnippet
                conversation = alignmentPrompt + loadRes(results) + currentConvo + makePostPrompt()
                #print(conversation)

                # create new response to user incorporating google search knowledge
                chatResponse = chatComplete(conversation, model=model, max_tokens=max_tokens, temperature=temperature, top_p=top_p, freq_p=freq_p, pres_p=pres_p)
                responseText = chatResponse.choices[0].message.content


            elif responseCheck[0] == '/;RTEXT':
                wfid = responseCheck[-1]
                rtext = rtxt(wfid)

                #don't append file to currentConvo
                rtxtSnippet = [{'role':'system', 'content':rtext}]
                conversation = alignmentPrompt + loadRes(results) + currentConvo + rtxtSnippet + makePostPrompt()
                #print(conversation)

                # create new response to user incorporating google search knowledge
                chatResponse = chatComplete(conversation, model=model, max_tokens=max_tokens, temperature=temperature, top_p=top_p, freq_p=freq_p, pres_p=pres_p)
                responseText = chatResponse.choices[0].message.content

            timestamp = time.time()
            timestring = str(datetime.fromtimestamp(timestamp))

            # create final assistant response from GPT completion by adding speaker and timestamp. This version will be stored in LTM, but such metadata is omitted from the vectorized versions
            formResponse = 'ASSISTANT at '+timestring+': '+responseText

            # store final assistant response in LTM database
            currentConvo.append({'role':'assistant', 'content':formResponse})
            currentText.append(responseText)
            identifier = str(uuid4())
            ids.append(identifier)
            cur.execute('INSERT INTO ChatHistory (id, message, speaker, timestamp, timestring) VALUES (?, ?, ?, ?, ?)', (identifier, formResponse, 'ASSISTANT', timestamp, timestring))
            conn.commit()
            cur.close()
            conn.close()

            # print assistant response
            print('\nASSISTANT: '+formResponse.split(sep=': ', maxsplit=1)[1])


