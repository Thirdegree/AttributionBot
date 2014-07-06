#gives credit to origional artists when possible
import praw, time, re, requests, os, sqlite3
from PIL import Image
from sys import argv
from collections import deque

r = praw.Reddit("AttributionBot by /u/thirdegree")

done = deque(maxlen=200)

def _login():
    USERNAME = raw_input("Username: ")
    r.login(USERNAME)
    return USERNAME


def main():
    #justSQLthings
    global conn
    conn = sqlite3.connect("hashes.db")
    global cursor
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE if not exists imghash (author text,source text, hash text)""")
    conn.commit()

    inbox = r.get_unread()
    for post in inbox:
        check_inbox_post(post)
        post.mark_as_read()


    subr = r.get_subreddit("thirdegree")
    for submission in subr.get_new():
        if submission.id not in done:
            done.append(submission.id)
            check_db(submission)

    
    conn.commit()

def check_inbox_post(post):
    pattern = r"Autor: *(.*?)\n\nSource: *(.*?)$"
    matches = re.match(pattern, post.body).groups()
    if not matches or len(matches) != 2:
        post.reply("I'm sorry, your post appears to be formatted incorrectly.")
    else:
        image = get_image(post.submission.url)
        try:
            picture = Image.open(image)
       
            
            imghash = dhash(picture)
            results = cursor.execute("""SELECT author, source FROM imghash WHERE hash=?""", (imghash, )).fetchone()
            if results:
                filtered_results = filter((lambda x: check_distance(x[2], imghash)), results)    
            else:
                filtered_results = []

            if filtered_results:
                pass
            else:
                cursor.execute("""INSERT INTO imghash(author, source, hash) VALUES (?, ?, ?)""", (matches[0], matches[1], imghash))

            os.remove(image)
        except IOError:
            os.remove(image)

def check_db(submission):
    image = get_image(submission.url)
    try:
        picture = Image.open(image)
    
        imghash = dhash(picture)
        results = cursor.execute("""SELECT author, source, hash FROM imghash""").fetchall()

        if results:
            print check_distance(results[0][2], imghash)
            filtered_results = filter((lambda x: check_distance(x[2], imghash)), results)
        else:
            filtered_results = []

        if filtered_results:
            result = filtered_results[0]
            submission.add_comment("Author: %s\n\n Origional: %s"%(result[0], result[1]))
        else:
            submission.add_comment("Author unknown. If you know the autor and origional source, please reply in the form \n\n    Autor: name\n    Source: URL \n\n Thanks for your help!")
        os.remove(image)
    except IOError:
        os.remove(image)



def get_image(url):
    img = requests.get(url, stream=True)
    path = str(time.clock()*100000)[:-2] + ".jpg"
    with open(path, 'wb') as to:
        for chunk in img.iter_content():
            to.write(chunk)
    return path

# Source for dhash: 
# http://blog.iconfinder.com/detecting-duplicate-images-using-python/
def dhash(image, hash_size=8):    
    # Grayscale and shrink the image in one step.
    image = image.convert('L').resize(
        (hash_size + 1, hash_size),
        Image.ANTIALIAS,
        )
 
    pixels = list(image.getdata())
 
    # Compare adjacent pixels.
    difference = []
    for row in xrange(hash_size):
        for col in xrange(hash_size):
            pixel_left = image.getpixel((col, row))
            pixel_right = image.getpixel((col + 1, row))
            difference.append(pixel_left > pixel_right)
 
    # Convert the binary array to a hexadecimal string.
    decimal_value = 0
    hex_string = []
    for index, value in enumerate(difference):
        if value:
            decimal_value += 2**(index % 8)
        if (index % 8) == 7:
            hex_string.append(hex(decimal_value)[2:].rjust(2, '0'))
            decimal_value = 0
 
    return ''.join(hex_string)

# http://en.wikipedia.org/wiki/Hamming_distance#Algorithm_example
def hamming_distance(s1, s2):
    #Return the Hamming distance between equal-length sequences
    if len(s1) != len(s2):
        raise ValueError("Undefined for sequences of unequal length")
    return sum(ch1 != ch2 for ch1, ch2 in zip(s1, s2))

def check_distance(s1, s2):
    distance = hamming_distance(s1,s2)
    if len(argv) == 1:
        if distance <= 10:
            return True
    else:
        if distance <= int(argv[1]):
            return True
    return False

if __name__ == '__main__':
    _login()
    while True:
        try:
            main()
        except:
            time.sleep(100)