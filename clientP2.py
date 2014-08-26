#library to include
import socket
import sys
import smtplib
import httplib2
import urllib2
import os
import xml.etree.ElementTree as ET
from socket import AF_INET, SOCK_STREAM
from select import select
from apiclient.discovery import build
from apiclient.http import MediaFileUpload
from oauth2client.client import OAuth2WebServerFlow
from apiclient import errors

#global file write object
f = open('activity.log', 'w')

def nameInList(name, aList):
    # find number of users
    size = len(aList)
    i = 0
    # loop until name is found, or if you fall off of list
    while i < size:
        if name == aList[i]:
            return i
        else:
            i = i + 1
    # return error code (not in list)
    return -1

def chatWithFriends(myID, myIP, myPort, friendNames, friendLocs, myURL):
    #set up welcome port
    welcomeSocket = socket.socket(AF_INET, SOCK_STREAM)
    welcomeSocket.bind(('', int(myPort)))
    # set flag
    keepChatting = True
    chatIn = False
    chatOut = False
    #set variable names
    remainder = ''
    inFriendName = ''
    outFriendName = ''
    inCounter = 0
    outCounter = 0
    chatInSocket = socket.socket(AF_INET, SOCK_STREAM)
    chatOutSocket = socket.socket(AF_INET, SOCK_STREAM)
    #create list of inputs to listen to
    inputList = []
    inputList.append(welcomeSocket)
    inputList.append(sys.stdin)
    #create dictionary of open chats
    openChats = {}
    # have welcome socket listen (up to 5 requests at once)
    welcomeSocket.listen(5)
    #print chat welcome message
    print 'Welcome to chat mode!\n\tPress s to start a chat,\n\tt to terminate a chat session,\n\tor q to quit chat mode'
    f.write('user entering chat mode\n')
    # start chat loop
    while keepChatting:
        #poll for inputs
        read, write, error = exception = select(inputList,[],[])
        #go through every input operation
        for s in read:
            #check for welcome socket
            if s == welcomeSocket:
                #if you do not already have a chat initalized by a friend
                if not chatIn:
                    #accept connection
                    chatInSocket, usrAddress = welcomeSocket.accept()
                    # get friend message
                    friendMessage, remainder = getTCPmessage(chatInSocket, remainder)
                    #find friend name
                    friendSplit = friendMessage.split()
                    inFriendName =friendSplit[1]
                    #create confirm message
                    confirmMessage = 'CONFIRM ' + myID + '\n'
                    chatInSocket.sendall(confirmMessage)
                    print 'you are not chatting with ' + inFriendName + ', type his name followed by a message to send this user a message'
                    f.write('user chatting with ' + inFriendName + '\n')
                    #add in chat socket to list of things to listen to
                    inputList.append(chatInSocket)
                    #set flag
                    chatIn = True
                    inCounter = 0
                else:
                    print 'someone is trying to chat with you, but you cannot answer'
                    f.write('message ignored, cannot support more than 2 inbound chat sessions\n')
                    chatInSocket2, usrAddress = welcomeSocket.accept()
                    chatInSocket2.close()

            elif s == chatInSocket:
                #get message
                chatMessage, remainder = getTCPmessage(chatInSocket, remainder)
                f.write('recieved message: ' + chatMessage + ' from ' + inFriendName + '\n')
                #see what the message was
                if ChatMessage[0] == 'C':
                    #parse message                
                    chatParsed, end = chatMessage.split(' ', 1)
                    #split chat counter and message
                    endSplit = end.split(' ', 1)
                    #print message from friend
                    print inFriendName + ': ' + endSplit[1]
                    #send delivered message
                    deliveredMessage = 'DELIVERED ' + endSplit[0] + '\n'
                    chatInSocket.sendall(deliveredMessage) 
                    f.write('responded with ' + deliveredMessage + '\n' )
                elif chatMessage == 'TERMINATE':
                    #close chat socket
                    chatInSocket.close()
                    #tell user what happened
                    print 'user ' + inFriendName + ' terminated chat session'
                    #remove chat socket from listening list
                    inputList.remove(chatInSocket)
                    #set input chat flag
                    chatIn = False
                    f.write('terminated chat with ' + infFriendName + '\n')
                

            #keyboard input
            elif s == sys.stdin:
                # get input
                chatInput = sys.stdin.readline()
                chatInput = chatInput.replace('\n', '')
                
                if chatInput == 's':
                    if not chatOut:
                        tempFriendName = raw_input('Enter the name of the friend you want to chat with: ')
                        #if this person is your friend
                        output = nameInList(tempFriendName, friendNames)
                        if output != -1:
                            #set chat name
                            outFriendName = tempFriendName
                            #get friend info
                            lookUpURL = friendLocs[output]
                            #temporarily download friend location file
                            downloadFriendFile(lookUpURL, 'tempLoc.xml')
                            #get XML tree
                            tempLocation = ET.parse('tempLoc.xml')
                            tempRoot = tempLocation.getroot()
                            #parse out user port and IP address
                            friendIP = tempRoot[0][1].text
                            friendPort = tempRoot[0][2].text
                            f.write('attempting to chat with ' + tempFriendName + '\n')
                            #see if user is online
                            if friendPort != '0':
                                #make a connection to friend
                                chatOutSocket = socket.socket(AF_INET, SOCK_STREAM)
                                print friendIP
                                print friendPort
                                chatOutSocket.connect((friendIP, int(friendPort)))
                                # send friend request to friend
                                friendReq = 'FRIEND ' + myID + ' ' + myURL + '\n'
                                chatOutSocket.sendall(friendReq)
                                #get confirm message
                                friendConfirm, remainder = getTCPmessage(chatOutSocket, remainder)
                                #add chat socket to listening list
                                inputList.append(chatOutSocket)
                                #tell user of connection
                                print 'now chatting with ' + outFriendName
                                f.write('now chatting with ' + outFriendName + '\n')
                                outCounter = 0
                            else:
                                #user is not online, do not attempt to connect
                                print 'user ' + outFriendName + ' is not online'
                                f.write('user ' + outFriendName + ' is not online\n')
                        else:
                            #report that user is not currently your friend
                            print tempFriendName + ' is not your friend, cannot establish chat connection'
                    else:
                        print 'cannot do two outbound chats at once'
                        f.write('cannot chat with more than two outbound connections\n')

                elif chatInput == 't':
                    #get name
                    chatToRemove = raw_input('enter name of friend you want to terminate chat with: ')
                    #check name
                    if chatToRemove == inFriendName and chatIn == True:
                        #send terminate message
                        chatInSocket.sendall('TERMINATE \n')
                        #close chat socket
                        chatInSocket.close()
                        #set flag
                        chatIn = False
                        #remove socket from listen list
                        inputList.remove(chatInSocket)
                        inFriendName = ''
                        #tell user of operation
                        print 'terminated chat with ' + chatToRemove
                        f.write('terminating chatting with ' +chatToRemove + '\n')
                        
                    elif chatToRemove == outFriendName and chatOut == True:
                        #send terminate message
                        chatOutSocket.sendall('TERMINATE \n')
                        #close chat socket
                        chatOutSocket.close()
                        #set flag
                        chatout = False
                        #remove socket from listen list
                        inputList.remove(chatOutSocket)
                        outFriendName = ''
                        #tell user of operation
                        print 'terminated chat with ' + chatToRemove
                        f.write('terminating chat with ' + chatToRemove + '\n')

                    else:
                        print 'you are not chatting with ' + chatToRemove
                        f.write('cannot terminate chat with ' +chatToRemove + ', because you are not chatting with that person\n')

                elif chatInput == 'q':
                    #tell user you are quitting chat mode
                    print 'quitting chat mode'
                    #check if any chat connections are open
                    if inFriendName != '':
                        #end chat session
                        chatInSocket.sendall('TERMINATE \n')
                        #close chat socket
                        chatInSocket.close()
                        f.write('terminating chat with ' + inFriendName + '\n')
                    if outFriendName != '':
                        #end chat session
                        chatOutSocket.sendall('TERMINATE \n')
                        #close chat socket
                        chatOutSocket.close()
                        f.write('terminating chat with ' + inFriendName + '\n')
                    #end function
                    return 0
                #user wants to try chatting with a friend
                else:
                    #get friend name
                    chatSplit = chatInput.split(' ', 1)
                    #see if in chat with that name
                    if chatSplit[0] == inFriendName:
                        #make message
                        message = 'CHAT ' + str(inCounter) + ' ' + chatSplit[1] + '\n'
                        #send message
                        chatInSocket.sendall(message)
                        f.write('sent message to ' + inFriendName + ': ' + message + '\n')
                        #get delivered message
                        delivered, remainder = getTCPmessage(chatInSocket, remainder)
                        #incriment in counter
                        inCounter = inCounter + 1
                        f.write('recieved message from ' + inFriendName + ': ' + delivered + '\n')
                    elif chatSplit[0] == outFriendName:
                        #make message
                        message = 'CHAT ' + str(outCounter) + ' ' + chatSplit[1] + '\n'
                        #send message
                        chatOutSocket.sendall(message)
                        f.write('sent message to ' + outFriendName + ': ' + message + '\n')
                        #get delivered message
                        delivered, remainder = getTCPmessage(chatOutSocket, remainder)
                        #incriment in counter
                        outCounter = outCounter + 1
                        f.write('recieved message from ' + outFriendName + ': ' + delivered + '\n')
                    else:
                        #not in chat with that friend
                        print 'you are not chatting with ' + chatSplit[0]
                        f.write('cannot send chat to ' + inFriendName + '\n')

            #input from a chat message
            elif s == chatOutSocket:
                #get chat message
                message, remainder = getTCPmessage(chatOutSocket, remainder)
                f.write('recieved message ' + message + ' from ' + outFriendName + '\n')
                #parse message
                messageParsed, end = message.split(' ', 1)
                if messageParsed[0] == 'CHAT':
                    #split chat counter and message
                    endSplit = end.split(' ', 1)
                    #print message from friend
                    print 'HORSE'
                    print outFriendName + ': ' + endSplit[1]
                    #send delivered message
                    deliveredMessage = 'DELIVERED ' + endSplit[0] + '\n'
                    chatOutSocket.sendall(deliveredMessage) 
                    f.write('sent message ' + deliveredMessage + ' to ' + outFriendName + '\n')
                elif messageParsed[0] == 'TERMINATE':
                    #close chat socket
                    chatoutSocket.close()
                    #tell user what happened
                    print 'user ' + outFriendName + ' terminated chat session'
                    #remove chat socket from listening list
                    inputList.remove(chatInSocket)
                    f.write('terminating chat with ' + outFriendName + '\n')
                    #set input chat flag
                    chatOut = False
    #end of function
    return 0
                

def getTCPmessage(tcpSocket, lastMessage):
    message = ''    
    getMoreData = True
    while getMoreData:
        message = tcpSocket.recv(2048)
        lastMessage += message
        # if delimiter found
        if lastMessage.find('\n') != '-1':
            # break out of loop
            getMoreData = False
        # split apart 
    try:
        realMessage, remainder = lastMessage.split('\n', 1)
    except:
        print 'an error happened'
        
    return [realMessage, remainder]

def fileExists(fileName):
    #if file exists
    if os.path.exists(fileName):
        return True
    #file does not exist
    else:
        return False

def retrieve_all_files(service):
    #initalize result and token
    result = []
    page_token = None
    #loop until further notice
    while True:
        try:
            param = {}
            #if not first iteration
            if page_token:
                #insert page token
                param['pageToken'] = page_token
            #get file info from token
            files = service.files().list(**param).execute()
            #add to result list
            result.extend(files['items'])
            #get next token
            page_token = files.get('nextPageToken')
            #if no more items, break
            if not page_token:
                break
        #catch errors
        except errors.HttpError, error:
            print 'An error occurred: %s' % error
            break
    #return list of drive files
    return result

def downloadFriendFile(fileURL, fileName):
    #
    urllib2.Request(fileURL, headers={'Accept': 'text/xml'})
    #get file instance
    response = urllib2.urlopen(fileURL)
    #open file for writing
    newFile = open(fileName, 'w')
    #write the url response to the file
    newFile.write(response.read())
    newFile.close()

def updateFile(service, fileID, fileName):
    try:
        #retrieve old file info
        fileToUpdate = service.files().get(fileId=fileID).execute()
        #get new content for file
        media_body = MediaFileUpload(fileName, mimetype='text/xml', resumable=True)
        #send request to drive
        updatedFile = service.files().update(fileId=fileID, body=fileToUpdate, newRevision=False, media_body=media_body).execute()
        #return new file object
        return updatedFile
    #handle error is one occurs
    except errors.HttpError, error:
        print 'an error occured: %s' % error
        return None

def getDriveFiles(service):
    result = []
    page_token = None
    print 'HELP\n'

    while True:
        try:
            param = {}
            if page_token:
                param['pageToken'] = page_token
            files = service.files().list(**param).execute()
            print 'FUNCTION: ' + files
            print '\n'
            result.extend(files['items'])
            page_token = files.get('nextPageToken')
            if not page_token:
                break
        except errors.HttpError, error:
            print 'an error has occured %s' % error
            break
    return result
            

#prints menu and returns the command given by user
def printMenu():
    print "welcome to the CPE 400 social network, choose an option below"
    print "\t1) <S>end friend request"
    print "\t2) <G>o into chat mode"
    print "\t3) <L>ook at your friends list"
    print "\t4) <A>dd a friends location file"
    print "\t5) <U>pdate your files"
    print "\t6) <Q>uit social network"
    command = raw_input("Command: ")
    return command

#sends friend request to given e-mail address
def sendFriendRequest(locationURL):
    #set host email info
    gmail_user = "socialnetworkhost@gmail.com"
    gmail_pwd = "cpe400user"
    FROM = 'socialnetworkhost@gmail.com'
    #get email address the user wants to send request to
    friendEmail = raw_input("Enter the e-mail address you want to send a friend request to: ")
    myEmail = raw_input("Enter the email you want your friend to respond to: ")
    TO = [friendEmail] #must be a list
    SUBJECT = "I want to be your friend!"
    TEXT = "Hello! I want to be your friend on the CPE 400 social network.\nEnter the following url into your client to get my information:\n\n" + locationURL + "\n\nPlease send an e-mail back to " + myEmail + " to complete this friendship\n\n"
    #prepare actual message
    message = """\From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
    #attempt to send message
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_pwd)
        server.sendmail(FROM, TO, message)
        server.close()
        print 'successfully sent the mail'
        f.write('friend request sent to ' + friendEmail + '\n')
    except:
        print "failed to send mail" 
        f.write('friend request failed when sending to ' + friendEmail + '\n')   


#start program

#initalize ID and secret
CLIENT_ID = '147036946120-q7c7b2kjcsrtleaqgrnpf2k7v4d1sqs9.apps.googleusercontent.com'
CLIENT_SECRET = 'jrKT7GishTzcDHRr15q7orxC'
#choose scope in which to use
OAUTH_SCOPE = 'https://www.googleapis.com/auth/drive'
#redirect URI for installed apps
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'
#run through the OAuth flow and retrieve credentials
flow = OAuth2WebServerFlow(CLIENT_ID, CLIENT_SECRET, OAUTH_SCOPE, REDIRECT_URI)
#check verification code file
authorize_url = flow.step1_get_authorize_url()
#tell user what link to go to
print 'Go to the following link in your browser: ' + authorize_url
#get new verification code
verificationCode = raw_input('\nEnter verification code: ').strip()
#save verification code to file
credentials = flow.step2_exchange(verificationCode)
f.write('successfully conected \n')
#create an httplib2.Http object and authorize it with our credentials
http = httplib2.Http()
http = credentials.authorize(http)
#use credentials to connect to drive
drive_service = build('drive', 'v2', http=http)
#get list of files in drive
listData = retrieve_all_files(drive_service)
f.write('recieved list data from drive \n')
#see if you already have friends
if fileExists('friendNames.txt'):
    #if list data exists, get the data for it
    listLocFile = open('friendLocs.txt', 'r')
    listNameFile = open('friendNames.txt', 'r')
    #get the list info for the IDs and names
    friendNames = listNameFile.read().split()
    friendLocs = listLocFile.read().split()
    #close the files
    listNameFile.close()
    listLocFile.close()
    f.write('recieved friend list from file \n')
#otherwise, initalize friend lists
else:
    friendNames = []
    friendLocs = []
    f.write('friend file not found, creating new friend list \n')


#path to the location file to upload
locationFILENAME = 'location.xml'
#set your location to the users spesified location
location = ET.parse(locationFILENAME)
root = location.getroot()
#change location file to online
myIP = raw_input('\nEnter your IP address: ')
myPort = raw_input('Enter your Port number: ')
root[0][1].text = myIP
root[0][2].text = myPort
myID = root[0][0].text
#write the new xml file
location.write(locationFILENAME)
#initalize media body and the body itself
locationMedia_body = MediaFileUpload(locationFILENAME, mimetype='text/xml', resumable=True)
locationBody = {
  'title': 'location.xml',
  'description': 'gives user location info',
  'mimeType': 'text/xml'
}
#upload new location file to drive
#loop through your drive list
for aFile in listData:
    #if location file found
    if aFile['originalFilename'] == 'location.xml':
        #get its download URL
        myLocation = aFile['webContentLink']
        #update the file
        updateFile(drive_service, aFile['id'], 'location.xml')
        f.write('updated location.xml in drive \n')



#show menu (loop)
keepGoing = True
while keepGoing:
    command = printMenu()
    #do command operation
    if command == '1' or command == 's' or command == 'S':
        #send friend request
        sendFriendRequest(myLocation)
        print myLocation

    elif command == '2' or command == 'g' or command == 'G':
        #run chat function
        chatWithFriends(myID, myIP, myPort, friendNames, friendLocs, myLocation)

    elif command == '3' or command == 'l' or command == 'L':
        #print list of friends
        print friendNames

    elif command == '4' or command == 'a' or command == 'A':
        #prompt user for URL
        newURL = raw_input('Enter the URL of your friends locaiton file: ')
        #append new url to list of friends locations
        friendLocs.append(newURL)
        #get friend location file
        downloadFriendFile(newURL, 'tempLoc.xml')
        #get data from file
        tempLocation = ET.parse('tempLoc.xml')
        tempRoot = tempLocation.getroot()
        #find the users userID
        newName = tempRoot[0][0].text
        #append name to end of friend name list
        friendNames.append(newName)
        #remove temporary file
        os.remove('tempLoc.xml')
        f.write('friend ' + newName + ' added\n')

    elif command == '5' or command == 'u' or command == 'U':
        #loop throught drive files
        for driveFile in listData:
            #update each file 
            updateFile(drive_service, driveFile['id'], driveFile['originalFilename'])
        print 'all drive files have been updated\n'
        f.write('all drive files updated\n')

    elif command == '6' or command == 'q' or command == 'Q':
        #end program
        keepGoing = False
        f.write('ending program\n')

#change location file and re-upload to drive
locationEND = ET.parse(locationFILENAME)
rootEND = locationEND.getroot()
#change location file to offline
rootEND[0][1].text = '0.0.0.0'
rootEND[0][2].text = '0'
#write the new xml file
locationEND.write(locationFILENAME)
#initalize media body and the body itself
updatedMedia_body = MediaFileUpload(locationFILENAME, mimetype='text/xml', resumable=True)
body = {
  'title': 'location.xml',
  'description': 'gives user location info',
  'mimeType': 'text/xml'
}

print "Exiting social network, goodbye :)"
#update new location file to drive
for aFile in listData:
    #if location file found
    if aFile['originalFilename'] == 'location.xml':
        #update the file
        updateFile(drive_service, aFile['id'], 'location.xml')
        f.write('updated location file (offline)\n')

#save current friend list
namesF = open('friendNames.txt', 'w')
for name in friendNames:
    namesF.write(name)
    namesF.write(' ')
namesF.close()
locsF = open('friendLocs.txt', 'w')
for location in friendLocs:
    locsF.write(location)
    locsF.write(' ')
f.write('wrote friends list\n')
locsF.close()
#close output file
f.close()


















        
