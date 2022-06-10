import socket
import select
import chatlib
import random
import json

IP = socket.gethostbyname(socket.gethostname())
PORT = 6853

users = {}
questions = {}
logged_users = {}
messages_to_send = []
data_queue = {}
CORRECT_ANSWER_POINTS = 5
WRONG_ANSWER_POINTS = 0


def build_and_send_message(server_socket, code, msg):
    """
    Builds a new message using Protocol, wanted code and message.
    Prints debug info, then sends it to the given socket.
    Parameters: conn (socket object), code (str), msg (str)
    Returns: Nothing
    """
    message = chatlib.build_message(code, msg)
    server_socket.sendall(message.encode())


def recv_message_and_parse(server_socket):
    """
    Receives a new message from given socket.
    Prints debug info, then parses the message using Protocol.
    Parameters: conn (socket object)
    Returns: cmd (str) and data (str) of the received message.
    If error occurred, will return None, None
    """
    try:
        data = server_socket.recv(10021).decode()
        cmd, msg = chatlib.parse_message(data)
        if cmd != chatlib.ERROR_RETURN or msg != chatlib.ERROR_RETURN:
            return cmd, msg
        else:
            return chatlib.ERROR_RETURN, chatlib.ERROR_RETURN
    except ConnectionResetError:
        return chatlib.ERROR_RETURN, chatlib.ERROR_RETURN


def setup_socket():
    """
    Creates new listening socket and returns it
    Receives: -
    Returns: the socket object
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(f"Server is up on {IP} on port {PORT}")
    sock.bind((IP, PORT))
    sock.listen(20)
    return sock


def handle_client_message(server_socket, cmd, data):
    """
    Gets message code and data and calls the right function to handle command
    Receives: socket, message code and data
    Returns: None
    """
    hostname = server_socket.getpeername()
    if hostname not in logged_users.keys():
        pass
    if cmd == chatlib.PROTOCOL_CLIENT['login_msg']:
        handle_login_message(server_socket, data)
    else:
        username = logged_users[hostname]
        if cmd == chatlib.PROTOCOL_CLIENT['logout_msg']:
            handle_logout_message(server_socket)
        elif cmd == chatlib.PROTOCOL_CLIENT['getscore_msg']:
            handle_getscore_message(server_socket, username)
        elif cmd == chatlib.PROTOCOL_CLIENT['highscore_msg']:
            handle_highscore_message(server_socket)
            pass
        elif cmd == chatlib.PROTOCOL_CLIENT['logged_msg']:
            handle_logged_message(server_socket)
            pass
        elif cmd == chatlib.PROTOCOL_CLIENT['getquestion_msg']:
            handle_question_message(server_socket)
        elif cmd == chatlib.PROTOCOL_CLIENT['sendanswer_msg']:
            handle_answer_message(server_socket, username, data)
            pass
        else:
            send_error(server_socket, 'Error: Unrecognized command')
            return


def handle_login_message(server_socket, data):
    """
    Gets socket and message data of login message. Checks  user and pass exists and match.
    If not - sends error and finished. If all ok, sends OK message and adds user and address to logged_users
    Receives: socket, message code and data
    Returns: None (sends answer to client)
    """
    client_hostname = server_socket.getpeername()
    username, password = data[:data.find("#")], data[data.find("#")+1:]
    if username not in users.keys():
        send_error(server_socket, 'The username you entered does not exist')
        return
    if users[username]['password'] != password:
        send_error(server_socket, 'Wrong password')
        return
    if users[username]['connected_ip'] != "":
        send_error(server_socket, 'User already connected')
        return
    logged_users[client_hostname] = username
    users[username]['connected_ip'] = client_hostname
    build_and_send_message(server_socket, chatlib.PROTOCOL_SERVER['login_ok_msg'], '')


def handle_logout_message(server_socket):
    """
    Closes the given socket
    Receives: socket
    Returns: None
    """
    client_hostname = server_socket.getpeername()
    if client_hostname in logged_users.keys():
        del logged_users[client_hostname]
    for user_attributes in users.values():
        if client_hostname in user_attributes.values():
            user_attributes["connected_ip"] = ""
    server_socket.close()


def handle_question_message(server_socket):
    global questions
    asked = []
    for user_attributes in users.values():
        if server_socket.getpeername() in user_attributes.values():
            asked = user_attributes["questions_asked"]
    all_questions = list(set(questions.keys())-set(asked))
    if not all_questions:
        build_and_send_message(server_socket, chatlib.PROTOCOL_SERVER['noquestions_msg'], "")
    else:
        rand_question_id = random.choice(all_questions)
        for user_attributes in users.values():
            if server_socket.getpeername() in user_attributes.values():
                user_attributes["questions_asked"].append(rand_question_id)
        chosen_question = questions[rand_question_id]
        question_text, answers = chosen_question['question'], chosen_question['answers']
        question_str = '#'.join([str(rand_question_id), question_text, answers[0], answers[1], answers[2], answers[3]])
        build_and_send_message(server_socket, chatlib.PROTOCOL_SERVER['question_msg'], question_str)


def handle_getscore_message(server_socket, username):
    """
    Sends to the socket YOURSCORE message with the user's score.
    Receives: socket and username (str)
    Returns: None (sends answer to client)
    """
    score = users[username]['score']
    build_and_send_message(server_socket, chatlib.PROTOCOL_SERVER['yourscore_msg'], str(score))


def handle_highscore_message(server_socket):
    """
    Sends to the socket HIGHSCORE message.
    Receives: socket
    Returns: None (sends answer to client)
    """
    global users
    highscore_str = ''
    users_and_scores = []
    for user in users.keys():
        users_and_scores.append((user, users[user]['score']))
    users_and_scores.sort(key=(lambda x: x[1]), reverse=True)
    for user, score in users_and_scores:
        highscore_str += '%s: %d\n' % (user, score)
    build_and_send_message(server_socket, chatlib.PROTOCOL_SERVER['highscore_msg'], highscore_str)


def handle_logged_message(server_socket):
    """
    Sends to the socket LOGGED message with all the logged users
    Receives: socket and username (str)
    Returns: None (sends answer to client)
    """
    global logged_users
    all_logged_users = logged_users.values()
    logged_str = ','.join(all_logged_users)
    build_and_send_message(server_socket, chatlib.PROTOCOL_SERVER['logged_msg'], logged_str)


def handle_answer_message(server_socket, username, data):
    splitted = data.split("#")
    if not splitted:
        send_error(server_socket, "Error: got no answer")
    try:
        question_id, answer = int(splitted[0]), int(splitted[1])
        answer_is_correct = questions[question_id]['correct'] == answer
        if answer_is_correct:
            users[username]['score'] += CORRECT_ANSWER_POINTS
            build_and_send_message(server_socket, chatlib.PROTOCOL_SERVER['correct_msg'], '')
        else:
            users[username]['score'] += WRONG_ANSWER_POINTS
            build_and_send_message(server_socket, chatlib.PROTOCOL_SERVER['wrong_msg'], str(questions[question_id]['correct']))
    except ValueError:
        send_error(server_socket, "Error: invalid input")


def send_error(server_socket, error_msg):
    """
    Send error message with given message
    Receives: socket, message error string from called function
    Returns: None
    """
    build_and_send_message(server_socket, chatlib.PROTOCOL_SERVER["error_msg"], error_msg)


def print_client_sockets(client_sockets):
    for cl in client_sockets:
        print('\t', cl.getpeername())


def load_questions():
    """
    Loads questions bank from file
    Receives: -
    Returns: questions dictionary
    """
    with open('Questions.txt') as f:
        qs = json.loads(f.read())
        new_qs = {int(key): value for key, value in qs.items()}
        return new_qs


def load_user_database():
    """
    Loads users list from file
    Receives: -
    Returns: user dictionary
    """
    with open('Users.txt') as f:
        return json.loads(f.read())


def main():
    global users
    global questions
    users = load_user_database()
    questions = load_questions()
    server = setup_socket()
    client_sockets = [server]

    while True:
        read_list, write_list, exceptional_list = select.select(client_sockets, client_sockets, [])
        for server_socket in read_list:
            if server_socket is server:
                client, address = server.accept()
                print(f'Client {address} connected')
                client_sockets.append(client)
            else:
                cmd, data = recv_message_and_parse(server_socket)
                if cmd is None or cmd == chatlib.PROTOCOL_CLIENT['logout_msg']:
                    handle_logout_message(server_socket)
                    client_sockets.remove(server_socket)
                    print(f'Connection terminated')
                else:
                    handle_client_message(server_socket, cmd, data)
        for message in messages_to_send:
            conn, data = message
            if server_socket in write_list:
                while server_socket in client_sockets:
                    conn.sendall(data.encode())
                messages_to_send.clear()


if __name__ == '__main__':
    main()
