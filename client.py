import socket
import chatlib


def build_and_send_message(client_socket, code, msg):
    """
    Builds a new message using Protocol, wanted code and message.
    Prints debug info, then sends it to the given socket.
    Paramaters: conn (socket object), code (str), msg (str)
    Returns: Nothing
    """
    message = chatlib.build_message(code, msg)
    client_socket.sendall(message.encode())
    # print("The server was sent the following: ")
    # print(f"Command: {code}, message: {msg}")


def recv_message_and_parse(client_socket):
    """
    Recieves a new message from given socket.
    Prints debug info, then parses the message using Protocol.
    Paramaters: conn (socket object)
    Returns: cmd (str) and data (str) of the received message.
    If error occurred, will return None, None
    """
    data = client_socket.recv(10021).decode()
    cmd, msg = chatlib.parse_message(data)
    if cmd != chatlib.ERROR_RETURN or msg != chatlib.ERROR_RETURN:
        # print(f"The server sent: {data}")
        # print(f"command: {cmd}, message: {msg}")
        return cmd, msg
    else:
        return chatlib.ERROR_RETURN, chatlib.ERROR_RETURN


def build_send_recv_parse(client_socket, cmd, msg):
    build_and_send_message(client_socket, cmd, msg)
    command, message = recv_message_and_parse(client_socket)
    return command, message


def connect():
    conn_confirm = False
    client = None
    while not conn_confirm:
        ip = input("Enter IP address: ")
        port = input("Enter Port: ")
        print(f"Attempting to connect to ({ip}, {port})...")
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(5)
        try:
            client.connect((ip, int(port)))
            print("Connection successful, You are connected.")
            conn_confirm = True
        except:
            print("Could not connect.")
    return client


def login(client_socket):
    login_bool = False
    while not login_bool:
        username = input("Enter Username: ")
        password = input("Enter Password: ")
        list_login_data = [username, password]
        login_info = "#".join(list_login_data)
        message = chatlib.build_message(chatlib.PROTOCOL_CLIENT["login_msg"], login_info)
        client_socket.sendall(message.encode())
        command, message = recv_message_and_parse(client_socket)
        if command == chatlib.ERROR_RETURN or message == chatlib.ERROR_RETURN:
            error_and_exit("Unexpected error.")
        else:
            if command == chatlib.PROTOCOL_SERVER["login_failed_msg"]:
                if message != "":
                    print(f"The server refused to connect because of the error: {message}")
                else:
                    print("The server refused to connect because of an unknown reason.")
            elif command == chatlib.PROTOCOL_SERVER["login_ok_msg"]:
                login_bool = True
            else:
                print(f"The server sent an unexpected message: \n{command}\n{message}")
    print("Login successful.")


def play_question(client_socket):
    do_another = True
    ans = ""
    while do_another:
        command, message = build_send_recv_parse(client_socket, chatlib.PROTOCOL_CLIENT['getquestion_msg'], "")
        if command == chatlib.PROTOCOL_SERVER['question_msg']:
            question_id, question, ans1, ans2, ans3, ans4 = split_by_hash(message)
            print(f"Question {question_id}: {question}")
            print(f"1. {ans1}\n2. {ans2}\n3. {ans3}\n4. {ans4}\n")
            check_ans = False
            while not check_ans:
                ans = input("Enter your answer: ")
                if (ans[0] == '-' and ans[1:].isdigit()) or (ans.isdigit() and int(ans) > 4) or not ans.isdigit():
                    print("Invalid answer. Answer must be 1-4\n")
                else:
                    check_ans = True
            build_and_send_message(client_socket, chatlib.PROTOCOL_CLIENT["sendanswer_msg"], f"{question_id}#{ans}")
            cmd, msg = recv_message_and_parse(client_socket)
            if cmd == chatlib.PROTOCOL_SERVER["correct_msg"]:
                print("Answer Correct!")
            elif cmd == chatlib.PROTOCOL_SERVER["wrong_msg"]:
                print(f"Wrong answer( Correct answer was {msg}")
            answered = False
            while not answered:
                another = input("Would you like to keep playing? type y for yes and n for no ")
                if another.lower() == "y":
                    answered = True
                elif another.lower() == "n":
                    do_another = False
                    answered = True
                else:
                    print("Unexpected input, Try again.\n")
        elif command == chatlib.PROTOCOL_SERVER["noquestions_msg"]:
            print("No questions left.")
            print(get_highscore(client_socket))
            do_another = False


def get_menu():
    print("Available commands: ")
    print("To get a question, type question\nTo see logged users, type logged\nTo see your score, type score\n"
          "To see highscore table, type highscore\nTo logout of the game, type logout\nTo open game menu, type menu")


def get_logged_players(client_socket):
    cmd, msg = build_send_recv_parse(client_socket, chatlib.PROTOCOL_CLIENT["getlogged_msg"], "")
    if cmd == chatlib.PROTOCOL_SERVER["logged_msg"]:
        print(f"Logged players: \n{msg}")


def get_score(client_socket):
    cmd, msg = build_send_recv_parse(client_socket, chatlib.PROTOCOL_CLIENT["getscore_msg"], "")
    if cmd == chatlib.PROTOCOL_SERVER["yourscore_msg"]:
        print(f"Your score: {msg}")


def get_highscore(client_socket):
    cmd, msg = build_send_recv_parse(client_socket, chatlib.PROTOCOL_CLIENT["gethighscore_msg"], "")
    if cmd == chatlib.PROTOCOL_SERVER["highscore_msg"]:
        print(f"High score table: \n{msg}")


def logout(client_socket):
    build_and_send_message(client_socket, chatlib.PROTOCOL_CLIENT["logout_msg"], "")
    error_and_exit("Logged out.")


def error_and_exit(msg):
    print(f"The script was terminated because of the error:{msg}")
    exit()


def split_by_hash(msg):
    return msg.split("#")


def main():
    keep_going = False
    client_socket = connect()
    login(client_socket)
    get_menu()
    while not keep_going:
        command = input("Enter your desired command: ").lower().strip()
        if command == "logout":
            logout(client_socket)
            keep_going = True
        elif command == "question":
            play_question(client_socket)
        elif command == "score":
            get_score(client_socket)
        elif command == "highscore":
            get_highscore(client_socket)
        elif command == "menu":
            get_menu()
        elif command == "logged":
            get_logged_players(client_socket)
        else:
            print("Command not recognized, please try again.")


if __name__ == '__main__':
    main()
