import socket
import chatlib
import random
import select
from select import select
# GLOBALS
users = {}
questions = {}
logged_users = {}  # a dictionary of client hostnames to usernames - will be used later
messages_to_send = []
open_client_sockets = []
ERROR_MSG = "Error! "
SERVER_PORT = 5678
SERVER_IP = "127.0.0.1"


# HELPER SOCKET METHODS

def build_and_send_message(client_socket, cmd, msg):
    global messages_to_send
    message = chatlib.build_message(cmd, msg)
    add_message_to_queue(client_socket, message)
    print("[SERVER] ", message)  # Debug print


def recv_message_and_parse(client_socket):
    try:
        data = client_socket.recv(10211)
        data = data.decode()
        cmd, msg = chatlib.parse_message(data)
        if cmd is not None or msg is not None:
            print("[CLIENT ", cmd + " " + msg)
            return cmd, msg
        else:
            cmd, msg = '', ''
            return cmd, msg
    except ConnectionResetError:
        return None, None


def add_message_to_queue(client_socket, message):
    global messages_to_send
    messages_to_send.append((client_socket, message))


def send_waiting_messages(wait_list):
    global messages_to_send
    for message in messages_to_send:
        current_socket, data = message
        if current_socket in wait_list:
            current_socket.send(data.encode())
            messages_to_send.remove(message)


def split_msg(client_socket, msg, num):
    message = msg.split('#')
    if len(message) - 1 == num:
        return "the number of strings is: " + str(len(message))
    else:
        return None


def print_client_sockets():
    global logged_users
    for user in logged_users:
        print(user)


def load_user_database():
    """
    Loads users list from file	## FILE SUPPORT TO BE ADDED LATER
    Recieves: -
    Returns: user dictionary
    """
    list_of_users = open("users.txt").read().splitlines()
    users = {}
    for user_l in range(len(list_of_users)):
        user = list_of_users[user_l].split('#')
        username = user[0]
        password = user[1]
        score = user[2]
        questions_asked = []
        if len(user) > 3:
            question = user[3]
            question.split(',')
            if len(question) > 1:
                for q in range(len(question)):
                    questions_asked.append(question[q])
            else:
                questions_asked.append(user[3])
        if ',' in questions_asked:
            questions_asked.remove(',')
        users2 = {}
        users2["password"] = password
        users2["score"] = score
        users2["questions_asked"] = questions_asked
        users[username] = users2
    return users


def load_questions():
    """
    Loads questions bank from file	## FILE SUPPORT TO BE ADDED LATER
    Recieves: -
    Returns: questions dictionary
    """
    list_questions = open("questions.txt").read().split('\n')
    questions_to_load = {}
    for l in range(len(list_questions)):
        question = list_questions[l].split('#')
        #answers = [question[1], question[2], question[3], question[4]]
        ques = {"question": question[0], "answers": (question[1], question[2], question[3], question[4]),
                "correct": int(question[5])}
        questions_to_load[l] = ques

    return questions_to_load


def setup_socket():
    """
    Creates new listening socket and returns it
    Recieves: -
    Returns: the socket object
    """
    server_socket = socket.socket()
    server_socket.bind((SERVER_IP, SERVER_PORT))
    server_socket.listen(5)
    print("Server is up and running")
    return server_socket


def send_error(client_socket, error_msg):
    """
    Send error message with given message
    Recieves: socket, message error string from called function
    Returns: None
    """
    message = 'The server was closed due to: ' + error_msg
    build_and_send_message(client_socket, 'ERROR', message)


def create_random_question(username):
    global questions
    global users
    questions = load_questions()
    print(users[username]["questions_asked"])
    if len(users[username]["questions_asked"]) == len(questions):
        return None
    keep_appending = True
    while keep_appending:
        keep_appending = False
        question_id = random.choice(list(questions))
        if question_id in users[username]["questions_asked"]:
            keep_appending = True
    users[username]["questions_asked"].append(question_id)
    return str(str(question_id) + "#" + questions[question_id]["question"] + "#" + questions[question_id]["answers"][0] + "#" + questions[question_id]["answers"][1] + "#" + questions[question_id]["answers"][2] + "#" + questions[question_id]["answers"][3])


def handle_getscore_message(client_socket, username):
    global users
    user = users[username]
    print(user)
    score = user.get('score')
    build_and_send_message(client_socket, 'YOUR_SCORE' + str(score))


def handle_answer_message(client_socket, username, answer):
    global questions
    global users
    questions = load_questions()
    answer_id = int(answer.split("#")[0])
    clean_answer = answer.split("#")[1]
    if questions[answer_id]["correct"] == int(clean_answer):
        build_and_send_message(client_socket, 'CORRECT ANSWER', "")
        users[username]["score"] += 5
    else:
        build_and_send_message(client_socket, 'WRONG_ANSWER', str(questions[answer_id]["correct"]))


def handle_highest_score(client_socket):
    global users
    user_score = []
    user_score2 = []
    for us in users:
        user = users[us]
        score = users[us]["score"]
        print(score)
        user_score.append((us, score))
    for i in range(len(user_score)):
        user_score2.append((user_score[i][1], user_score[i][0]))
    user_score2.sort(reverse=True)
    print(user_score2)
    build_and_send_message(client_socket, 'ALL_SCORE', str(user_score2[0]) + "\n" + str(user_score2[1]) + "\n" + str(user_score2[2]) + "\n" + str(user_score2[3]) + "\n" + str(user_score2[4]))


def handle_logged_message(client_socket):
    global logged_users
    logged_users_list = logged_users.values()
    message = ""
    for user in logged_users_list:
        message += user + ","
    build_and_send_message(client_socket, 'LOGGED_ANSWER', message)


def handle_login_message(client_socket, data):
    """
    Gets socket and message data of login message. Checks  user and pass exists and match.
    If not - sends error and finished. If all ok, sends OK message and adds user and address to logged_users
    Recieves: socket, message code and data
    Returns: None (sends answer to client)
    """
    global users  # This is needed to access the same users dictionary from all functions
    global logged_users	 # To be used later
    cmd = data.split('#')
    u = split_msg(client_socket, data, 1)
    if u is not None:
        if cmd[0] not in logged_users.values():
            if cmd[0] in users:
                if users[cmd[0]].get('password') == cmd[1]:
                    build_and_send_message(client_socket, 'LOGIN_OK', "")
                    logged_users[client_socket.getpeername()] = cmd[0]
                else:
                    error_msg = 'You entered the wrong password'
                    send_error(client_socket, error_msg)
            else:
                error_msg = "You entered the wrong username"
                send_error(client_socket, error_msg)
        else:
            error_msg = "You are already connected"
            send_error(client_socket, error_msg)
    else:
        error_msg = "invalid value"
        send_error(client_socket, error_msg)


def handle_client_message(client_socket, cmd, data):
    """
    Gets message code and data and calls the right function to handle command
    Recieves: socket, message code and data
    Returns: None
    """
    global logged_users	 # To be used later
    global questions_asked
    global users
    if client_socket.getpeername() not in logged_users:
        if cmd == 'LOGIN':
            handle_login_message(client_socket, data)
    else:
        username = logged_users[client_socket.getpeername()]
        if cmd == 'MY_SCORE':
            handle_getscore_message(client_socket, username)
        elif cmd == 'GET_QUESTION':
            handle_question_message(client_socket, username)
        elif cmd == 'SEND_ANSWER':
            handle_answer_message(client_socket, username, data)
        elif cmd == 'LOGGED':
            handle_logged_message(client_socket)
        elif cmd == 'HIGHSCORE':
            handle_highest_score(client_socket)
        elif cmd == 'LOGOUT':
            handle_logout_message(client_socket)
        else:
            handle_logout_message(client_socket)


def handle_logout_message(client_socket):
    """
    Closes the given socket (in laster chapters, also remove user from logged_users dictioary)
    Recieves: socket
    Returns: None
    """
    global logged_users
    logged_users.pop(client_socket.getpeername())


def handle_question_message(client_socket, username):
    global users
    question = create_random_question(username)
    if question is not None:
        build_and_send_message(client_socket, 'YOUR_QUESTION', question)
    else:
        build_and_send_message(client_socket, 'NO_QUESTIONS', " No questions left")


def main():
    # Initializes global users and questions dictionaries using load functions, will be used later
    global users
    global questions
    users = load_user_database()
    questions = load_questions()
    server = setup_socket()
    client_sockets = [server]

    while True:
        read_list, write_list, exceptional_list = select.select(client_sockets, client_sockets, [])
        for conn in read_list:
            if conn is server:
                client, address = server.accept()
                print(f'Client {address} connected')
                client_sockets.append(client)
            else:
                cmd, data = recv_message_and_parse(conn)
                if cmd is None or cmd == chatlib.PROTOCOL_CLIENT['logout_msg']:
                    handle_logout_message(conn)
                    client_sockets.remove(conn)
                    print(f'Connection terminated')
                else:
                    handle_client_message(conn, cmd, data)

        for message in messages_to_send:
            conn, data = message
            if conn in write_list:
                while conn in client_sockets:
                    conn.sendall(data.encode())

                messages_to_send.clear()


if __name__ == '__main__':
    main()
