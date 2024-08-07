import bcrypt
import random
import string

def generate_password(length=8):
    """주어진 길이의 무작위 비밀번호 생성"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

def generate_username():
    """'vip' + 3자리 무작위 숫자로 구성된 사용자 이름 생성"""
    return 'vip' + ''.join(random.choice(string.digits) for _ in range(3))

def hash_password(password):
    """비밀번호 해싱"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def save_users(num_users=10):
    """사용자 이름과 비밀번호를 생성하고 해시화하여 파일에 저장"""
    with open('users.txt', 'w') as f:
        for _ in range(num_users):
            username = generate_username()
            password = generate_password()
            hashed_password = hash_password(password)
            f.write(f"{username}:{hashed_password.decode('utf-8')}\n")
            print(f"Generated - Username: {username}, Password: {password}")

if __name__ == "__main__":
    save_users()
