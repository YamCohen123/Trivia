import socket
import chatlib  # To use chatlib functions or consts, use chatlib.****
SERVER_IP = "127.0.0.1"  # Our server will run on same computer as client
SERVER_PORT = 5678


# HELPER SOCKET METHODS

def build_and_send_message(client_socket, cmd, msg):
    """
    Builds a new message using chatlib, wanted code and message.
    Prints debug info, then sends it to the given socket.
    Paramaters: conn (socket object), code (str), msg (str)
    Returns: Nothing
    """
    message = chatlib.build_message(cmd, msg)
    print(message)
    client_socket.send(message.encode())


def recv_message_and_parse(client_socket):
    """
    Recieves a new message from given socket.
    Prints debug info, then parses the message using chatlib.
    Paramaters: conn (socket object)
    Returns: cmd (str) and data (str) of the received message.
    If error occured, will return None, None
    """
    try:
        data = client_socket.recv(1024)
        data = data.decode()
        cmd, msg = chatlib.parse_message(data)
        if cmd is not None or msg is not None:
            print("[CLIENT ", cmd + " " + msg)
            return cmd, msg
        else:
            cmd, msg = ''
            return cmd, msg
    except ConnectionResetError:
        return None, None


def build_send_recv_parse(client_socket, cmd, data):
    build_and_send_message(client_socket, cmd, data)
    msg_code, msg = recv_message_and_parse(client_socket)
    return msg_code, msg


def connect():
    client_socket = socket.socket()
    client_socket.connect((SERVER_IP, SERVER_PORT))
    return client_socket


def login(client_socket):
    username = input("Please enter username: \n")
    password = input("Please enter password: \n")
    login_msg = chatlib.join_data([username, password])
    build_and_send_message(client_socket, 'LOGIN', login_msg)
    data = chatlib.parse_message(client_socket.recv(1024))
    response = str(data[:17])
    response = response.split()
    while response == "ERROR":
        username = input("login failed. enter username again: \n")
        password = input("login failed. enter username again: \n")
        login_msg = username + "#" + password
        build_and_send_message(client_socket, "LOGIN", login_msg)
        data = chatlib.parse_message(client_socket.recv(1024))
        response = str(data[:17])
        response = response.split()
    if response == "LOGIN_OK":
        print("login successful!")
        return


def error_and_exit(msg):
    print("The server was closed because due to: " + msg)
    exit()

def logout(client_socket):
    build_and_send_message(client_socket, chatlib.PROTOCOL_CLIENT["logout_msg"], "")


def get_logged_users(conn):
    (msg_code, msg) = build_send_recv_parse(conn, chatlib.PROTOCOL_CLIENT['getlogged_msg'], "")
    if msg_code == chatlib.PROTOCOL_SERVER["logged_msg"]:
        print(msg)


def play_question(client_socket):
    cmd, msg = build_send_recv_parse(client_socket, 'GET_QUESTION', "")
    if cmd == 'YOUR_QUESTION':
        print(msg)
        question_id = msg.split('#')[0]
        answer = input("Enter your guess: ")
        response_cmd, response_msg = build_send_recv_parse(client_socket, 'SEND_ANSWER', question_id + '#' + answer)
        if response_cmd == 'CORRECT_ANSWER':
            print("You are correct!")
        elif response_cmd == 'WRONG_ANSWER':
            print("You are wrong =(. Right answer is: " + response_msg)
        else:
            print('ERROR')
    elif msg == 'NO_QUESTIONS':
        print(msg)
    else:
        error_and_exit("ERROR")


def get_score(client_socket):
    cmd, msg = build_send_recv_parse(client_socket, 'MY_SCORE', "")
    if cmd == 'YOUR_SCORE':
        print(msg)
    else:
        error_and_exit("ERROR")


def get_highscore(client_socket):
    cmd, msg = build_send_recv_parse(client_socket, chatlib.PROTOCOL_CLIENT['gethighscore_msg'], "")
    if cmd == chatlib.PROTOCOL_SERVER["highscore_msg"]:
        print(msg)


def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ("127.0.0.1", 5678)
    client_socket.connect(server_address)
    login(client_socket)
    keep_going = True
    while keep_going:
        client_response = input(
            "Hello there player! To play, enter 1. To view your score, enter 2. To view the highscores, enter 3. To get logged users, enter 4. To log out, enter 5. To: ")
        if client_response == "1":
            play_question(client_socket)
        elif client_response == "2":
            username = input("Enter username")
            msg_code, msg = build_send_recv_parse(client_socket, 'MY_SCORE', username)
            print(msg.decode("utf-8"))
        elif client_response == "3":
            get_highscore(client_socket)
        elif client_response == "4":
            get_logged_users(client_socket)
        elif client_response == "5":
            logout(client_socket)
            keep_going = False
        else:
            print("Invalid Input")

if __name__ == '__main__':
    main()