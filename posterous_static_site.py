import requests
import json
import os
from time import sleep
from pprint import pprint
import re
from settings import *
import types

from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader(TEMPLATE_FOLDER))

def get_user_info():
    sleep(1) # posterous wants you to wait a second between api calls
    res = requests.get(
        "http://posterous.com/api/2/users/me",
        auth = (USERNAME, PASSWORD),
        data={"api_token":API_TOKEN}
    )
    assert res.status_code == 200
    return json.loads(res.content)

def get_site_list():
    sleep(1) # posterous wants you to wait a second between api calls
    res = requests.get(
        "http://posterous.com/api/2/sites",
        auth = (USERNAME, PASSWORD),
        data={"api_token":API_TOKEN}
    )
    assert res.status_code == 200
    return json.loads(res.content)

def post_iterator(site_id):
    page_number = 1
    while 1:
        count = 0
        for post in get_posts_for_site(site_id, page_number):
            count += 1
            yield post
        if count < 20:
            break
        page_number += 1

def get_posts_for_site(site_id, page_number):
    sleep(1) # posterous wants you to wait a second between api calls
    res = requests.get(
        "http://posterous.com/api/2/sites/%s/posts" % site_id,
        auth = (USERNAME, PASSWORD),
        data={"api_token":API_TOKEN, 'page':page_number}
    )
    assert res.status_code == 200
    return json.loads(res.content)

def create_index_page(posts):
    for post in posts:
        post['tidy_date'] = post["display_date"][:10].replace("/","-")
    template = env.get_template("index.html")
    f = open("%s/index.html"%SITE_FOLDER, "w")
    f.write( template.render(posts=posts) )
    f.close()

def create_post_page(post):
    # move the referenced images locally
    image_find_pattern = """<img [^>]*src=([^\s]+)[ \/]"""
    result = re.search(image_find_pattern, post['body_full'])
    if result:
        # if there are images, we should make a folder with the name of the slug and put the images in it
        if not os.path.exists("%s/%s"%(SITE_FOLDER, post['slug'])):
            os.mkdir("%s/%s"%(SITE_FOLDER, post['slug']))
        for group in result.groups():
            assert type(group) == types.UnicodeType
            # strip quote if they are on it
            if group[0] == '"' and group[-1] == '"':
                group = group[1:-1]
            pprint(group)
            res = requests.get(group)
            if res.status_code == 404:
                continue
            assert res.status_code == 200
            # move the images locally and replace the links
            image_filename = group.split("/")[-1]
            f = open("%s/%s/%s"%(SITE_FOLDER, post['slug'], image_filename), "w")
            f.write(res.content)
            f.close()
            # replace the link to the file in the html file so that it loads it locally
            post['body_full'] = post['body_full'].replace(group, "%s/%s"%(post['slug'], image_filename))
            #TODO: replace the link with the local file
    page_file_name = "%s.html" % post['slug']
    f = open("%s/%s"%(SITE_FOLDER, page_file_name), "w")
    template = env.get_template('post.html')
    f.write( template.render(content=post['body_full']) )
    f.close()

def process():
    sites = get_site_list()
    for site in sites:
        index_data = []
        for post in post_iterator(site['id']):
            print "processing url: %s" % post['full_url']
            create_post_page(post)
            # index list only contain important fields because content can be big for big blog
            index_data.append(post)
#            if len(index_data) > 2: break
        create_index_page(index_data)
        print "%s posts processed" % len(index_data)

if __name__ == "__main__":
    process()
