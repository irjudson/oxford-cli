#!/usr/bin/env python
#
# Project Oxford Command Line Interface
# by Ivan R. Judson
# 

import uuid
import datetime
import os
import shutil

# Python 2 or 3 import for urlparse
try:
    from urllib import parser as urlparse
except ImportError:
    import urlparse

# json for serialization, from the standard library 
import json
# requests makes things much more sane than the standard library
# http://docs.python-requests.org/en/latest/
import requests
# click provides the command line interpreter functionality
# http://click.pocoo.org/4/
import click

# Global variables
CONFIG_FILE="~/.projectoxford.json"
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

# Load API Key from config file
def load_config(filen):
    with open(os.path.expanduser(filen), 'r') as f:
        return json.load(f)

def save_config(filen, config):
     with open(os.path.expanduser(CONFIG_FILE), 'w') as f:
        json.dump(config, f)
       
# oxford is the command-line, it only has sub commands and two configuration options
# - a url to find the Project Oxford REST API
@click.group()
@click.option('--oxford-url', default='https://api.projectoxford.ai/', help='The url to the project oxford api.')
@click.pass_context
def oxford(ctx, oxford_url):
    ctx.obj = load_config(CONFIG_FILE)
    ctx.obj['oxford_url'] = oxford_url
   
#
# Face sub command: https://www.projectoxford.ai/doc/face/overview
#
@click.group()
@click.option('--apikey', envvar='OXFORD_FACE_APIKEY', default=None, help='Your API Key from http://https://dev.projectoxford.ai/.')
@click.pass_context
def face(ctx, apikey):
    if apikey:
        ctx.obj['apikeys']['face'] = apikey
    ctx.obj['oxford_url'] += 'face/v0'

@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('apikey')
@click.pass_context
def face_api_key(ctx, apikey):
    config = load_config(CONFIG_FILE)
    config['face'] = apikey
    save_config(CONFIG_FILE, config)
    
# a function to resolve if the input is an image file or a url
def resolve_input(ctx, param, value):
    # this will catch both http and https
    if value.startswith('http'):
        return urlparse.urlparse(value)
    else:
        return click.utils.open_file(value)
        
# detect a face in an image         
@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--analyzesfacelandmarks/--no-analyzesfacelandmarks', default=True, help='Optional parameter to get face landmarks.')
@click.option('--analyzesage/--no-analyzesage', default=True, help='Optional parameter to get age.')
@click.option('--analyzesgender/--no-analyzesgender', default=True, help='Optional parameter to get gender.')
@click.option('--analyzesheadpose/--no-analyzesheadpose', default=True, help='Optional parameter to get values of head-pose.')
@click.argument('image_path', callback=resolve_input)
@click.pass_context
def detect(ctx, analyzesfacelandmarks, analyzesage, analyzesgender, analyzesheadpose, image_path):
    """Detect faces in an image provided on the command line."""
    detection_path = '/detections'
    params = {
    'analyzesFaceLandmarks' : str(analyzesfacelandmarks).lower(),
    'analyzesAge' : str(analyzesage).lower(),
    'analyzesGender' : str(analyzesgender).lower(),
    'analyzesHeadPose' : str(analyzesheadpose).lower()
    }
    print ctx.obj
    headers = {
    'Ocp-Apim-Subscription-Key' : ctx.obj['apikeys']['face']
    }
    face_detect_url = ctx.obj['oxford_url'] + detection_path
    if type(image_path) is file:
        headers['Content-type'] = 'application/octet-stream'
        payload = image_path.read()
    if type(image_path) is urlparse.ParseResult:
        headers['Content-type'] = 'application/json'
        payload = json.dumps({ 'url' : image_path.geturl() })
    try:
        resp = requests.post(face_detect_url, params=params, data=payload, headers=headers)
        if resp.status_code == 200:
            print json.dumps(resp.json(), sort_keys=True, indent=2, separators=(',', ': '))
        else:
            print resp.json()['message']
    except Exception as e:
        print e
                
# find similar faces
@click.command(context_settings=CONTEXT_SETTINGS)
def find_similar():
    click.echo('Finds similar-looking faces of a specified face from a list of candidate faces.')

@click.command(context_settings=CONTEXT_SETTINGS)
def find_groups():
    click.echo('Divides candidate faces into groups based on face similarity.')

@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--maxnumofcandidatesreturned', default=1, help='Optional. Maximum number of the returned person candidates of each query. Valid range is 1-5. If not set, only the top 1 candidate will be returned.')
@click.option('--persongroupid', default=str(uuid.uuid4()), help='Target person group\'s ID')
@click.argument('faceid')
@click.pass_context
def identify(ctx, maxnumofcandidatesreturned, persongroupid, faceid):
    params = dict()
    identify_path = '/identifications'
    headers = {
    'Content-Type' : 'application/json',
    'Ocp-Apim-Subscription-Key' : ctx.obj['apikeys']['face']
    }
    identify_url = ctx.obj['oxford_url'] + identify_path
    payload = json.dumps({
        'subscription-key': ctx.obj['apikey'],
        'faceIds' : [faceid],
        'personGroupId' : persongroupid,
        'maxNumOfCandidatesReturned' : maxnumofcandidatesreturned,
        })
    try:
        resp = requests.post(identify_url, params=params, data=payload, headers=headers)
        if resp.status_code == 200:
            print json.dumps(resp.json(), sort_keys=True, indent=2, separators=(',', ': '))
        else:
            print resp.json()['message']
    except Exception as e:
        print e

@click.command(context_settings=CONTEXT_SETTINGS)
def verify():
    click.echo('Analyzes two faces and determine whether they are from the same person.')

#
# PersonGroup sub command: https://www.projectoxford.ai/doc/face/overview
#
@click.group()
@click.pass_context
def persongroup(ctx):
    pass

@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--persongroupid', default=str(uuid.uuid4()), help='User-provided name.')
@click.option('--customdata', default='', help='User-provided data attached to the person group. The size limit is 16KB.')
@click.argument('name')
@click.pass_context
def create_persongroup(ctx, customdata, name, persongroupid):
    params = dict()
    persongroups_create_path = '/persongroups/%s' % persongroupid
    headers = {
    'Content-Type' : 'application/json',
    'Ocp-Apim-Subscription-Key' : ctx.obj['apikeys']['face']
    }
    persongroup_create_url = ctx.obj['oxford_url'] + persongroups_create_path
    payload = json.dumps({
        'name' : name,
        'userData' : customdata,
        })
    try:
        resp = requests.put(persongroup_create_url, data=payload, params=params, headers=headers)
        if resp.status_code == 200:
            print "Created PersonGroup with id %s" % persongroupid
        else:
            print resp.json()['message']
    except Exception as e:
        print e
            
@click.command(context_settings=CONTEXT_SETTINGS)
@click.pass_context
def retrieve_all_persongroups(ctx):
    persongroups_path = '/persongroups'
    headers = {
    'Ocp-Apim-Subscription-Key' : ctx.obj['apikeys']['face']
    }
    persongroup_get_url = ctx.obj['oxford_url'] + persongroups_path
    try:
        resp = requests.get(persongroup_get_url, params=None, headers=headers)
        if resp.status_code == 200:
            print json.dumps(resp.json(), sort_keys=True, indent=2, separators=(',', ': '))
        else:
            print resp.json()['message']
    except Exception as e:
        print e

@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('persongroupid', required=True)
@click.pass_context
def retrieve_persongroup(ctx, persongroupid):
    persongroups_path = '/persongroups/%s' % persongroupid
    headers = {
    'Ocp-Apim-Subscription-Key' : ctx.obj['apikeys']['face']
    }
    persongroup_get_url = ctx.obj['oxford_url'] + persongroups_path
    try:
        resp = requests.get(persongroup_get_url, params=None, headers=headers)
        if resp.status_code == 200:
            print json.dumps(resp.json(), sort_keys=True, indent=2, separators=(',', ': '))
        else:
            print resp.json()['message']
    except Exception as e:
        print e

@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('persongroupid', required=True)
@click.pass_context
def list_people_in_persongroup(ctx, persongroupid):
    persongroups_path = '/persongroups/%s/persons' % persongroupid
    headers = {
    'Ocp-Apim-Subscription-Key' : ctx.obj['apikeys']['face']
    }
    persongroup_get_url = ctx.obj['oxford_url'] + persongroups_path
    try:
        resp = requests.get(persongroup_get_url, params=None, headers=headers)
        if resp.status_code == 200:
            print json.dumps(resp.json(), sort_keys=True, indent=2, separators=(',', ': '))
        else:
            print resp.json()['message']
    except Exception as e:
        print e
        
@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('persongroupid', required=True)
@click.pass_context
def training_status(ctx, persongroupid):
    persongroups_path = '/persongroups/%s/training' % persongroupid
    headers = {
    'Ocp-Apim-Subscription-Key' : ctx.obj['apikeys']['face']
    }
    persongroup_get_url = ctx.obj['oxford_url'] + persongroups_path
    try:
        resp = requests.get(persongroup_get_url, params=None, headers=headers)
        if resp.status_code == 200:
            print json.dumps(resp.json(), sort_keys=True, indent=2, separators=(',', ': '))
        else:
            print resp.json()['message']
    except Exception as e:
        print e

@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('persongroupid', required=True)
@click.pass_context
def train_persongroup(ctx, persongroupid):
    persongroups_path = '/persongroups/%s/training' % persongroupid
    headers = {
    'Ocp-Apim-Subscription-Key' : ctx.obj['apikeys']['face']
    }
    persongroup_get_url = ctx.obj['oxford_url'] + persongroups_path
    try:
        resp = requests.post(persongroup_get_url, params=None, headers=headers)
        if resp.status_code == 200:
            print json.dumps(resp.json(), sort_keys=True, indent=2, separators=(',', ': '))
        else:
            print resp.json()['message']
    except Exception as e:
        print e

@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--customdata', default='', help='User-provided data attached to the person group. The size limit is 16KB.')
@click.option('--name', default='', help='User-provided name.')
@click.argument('persongroupid', required=True)
@click.pass_context
def update_persongroup(ctx, customdata, name, persongroupid):
    params = dict()
    persongroups_update_path = '/persongroups/%s' % persongroupid
    headers = {
    'Content-Type' : 'application/json',
    'Ocp-Apim-Subscription-Key' : ctx.obj['apikeys']['face']
    }
    persongroup_create_url = ctx.obj['oxford_url'] + persongroups_update_path
    payload = json.dumps({
        'name' : name,
        'userData' : customdata,
        })
    try:
        resp = requests.patch(persongroup_create_url, data=payload, params=params, headers=headers)
        if resp.status_code == 200:
            print "Created PersonGroup with name %s" % persongroupid
        else:
            print resp.json()['message']
    except Exception as e:
        print e	

@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('persongroupid', required=True)
@click.pass_context
def delete_persongroup(ctx, persongroupid):
    persongroups_path = '/persongroups/%s' % persongroupid
    headers = {
    'Ocp-Apim-Subscription-Key' : ctx.obj['apikeys']['face']
    }
    persongroup_get_url = ctx.obj['oxford_url'] + persongroups_path
    try:
        resp = requests.delete(persongroup_get_url, params=None, headers=headers)
        if resp.status_code != 200:
            print resp.json()['message']
    except Exception as e:
        print e

#
# Person sub command
#
@click.group()
@click.pass_context
def person(ctx):
    pass

@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--faceid', required=True, help='At least one faceid for the person.')
@click.option('--persongroupid', required=True, help='The ID of the PersonGroup this person belongs to.')
@click.option('--customdata', default=None, help='User-provided data attached to the person group. The size limit is 16KB.')
@click.argument('name')
@click.pass_context
def create_person(ctx, faceid, persongroupid, customdata, name):
    person_create_url = ctx.obj['oxford_url'] + '/persongroups/%s/persons' % persongroupid
    params = dict()
    headers = {
    'Content-Type' : 'application/json',
    'Ocp-Apim-Subscription-Key' : ctx.obj['apikeys']['face']
    }
    payload = json.dumps({
        'name' : name,
        'userData' : customdata or "Created %s" % str(datetime.datetime.now()),
        'faceIds' : [faceid]
        })
    print payload
    print params
    print headers
    print person_create_url
    try:
        resp = requests.post(person_create_url, data=payload, params=params, headers=headers, verify=False)
        print resp
        if resp.status_code == 200:
            print "Created Person with id %s" % resp.json()['personId']
        else:
            print resp.json()['message']
    except Exception as e:
        print e

@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--persongroupid', required=True, help='The ID of the PersonGroup this person belongs to.')
@click.argument('personid', required=True)
@click.pass_context
def retrieve_person(ctx, persongroupid, personid):
    person_get_url = ctx.obj['oxford_url'] + '/persongroups/%s/persons/%s' % (persongroupid, personid)
    headers = {
    'Ocp-Apim-Subscription-Key' : ctx.obj['apikeys']['face']
    }
    try:
        resp = requests.get(person_get_url, params=None, headers=headers)
        if resp.status_code == 200:
            print json.dumps(resp.json(), sort_keys=True, indent=2, separators=(',', ': '))
        else:
            print resp.json()['message']
    except Exception as e:
        print e

@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--name', default='', help='User-provided name.')
@click.option('--faceid', required=True, help='At least one faceid for the person.')
@click.option('--persongroupid', required=True, help='The ID of the PersonGroup this person belongs to.')
@click.option('--customdata', default=None, help='User-provided data attached to the person group. The size limit is 16KB.')
@click.argument('personid')
@click.pass_context
def update_person(ctx, name, faceid, persongroupid, customdata, personid):
    person_update_url = ctx.obj['oxford_url'] + '/persongroups/%s/persons/%s' % (persongroupid, personid)
    params = dict()
    headers = {
    'Content-Type' : 'application/json',
    'Ocp-Apim-Subscription-Key' : ctx.obj['apikeys']['face']
    }
    payload = json.dumps({
        'name' : name,
        'userData' : customdata or "Updated at %s" % str(datetime.datetime.now()),
        'faceIds' : [faceid]
        })
    try:
        resp = requests.patch(person_update_url, data=payload, params=params, headers=headers, verify=False)
        print resp
        if resp.status_code != 200:
            print resp.json()['message']
    except Exception as e:
        print e

@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--persongroupid', required=True, help='The ID of the PersonGroup this person belongs to.')
@click.argument('personid', required=True)
@click.pass_context
def delete_person(ctx, persongroupid, personid):
    person_get_url = ctx.obj['oxford_url'] + '/persongroups/%s/persons/%s' % (persongroupid, personid)
    headers = {
    'Ocp-Apim-Subscription-Key' : ctx.obj['apikeys']['face']
    }
    try:
        resp = requests.delete(person_get_url, params=None, headers=headers)
        if resp.status_code == 200:
            print json.dumps(resp.json(), sort_keys=True, indent=2, separators=(',', ': '))
        else:
            print resp.json()['message']
    except Exception as e:
        print e
        
#
# PersonFace sub command
#
@click.group()
@click.pass_context
def personface(ctx):
    pass

@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--persongroupid', required=True, help='The ID of the PersonGroup this person belongs to.')
@click.option('--personid', required=True, help='The ID of the PersonGroup this person belongs to.')
@click.option('--faceid', required=True, help='At least one faceid for the person.')
@click.option('--customdata', default=None, help='User-provided data attached to the person group. The size limit is 16KB.')
@click.pass_context
def add_personface(ctx, persongroupid, personid, faceid, customdata):
    person_create_url = ctx.obj['oxford_url'] + '/persongroups/%s/persons/%s/faces/%s' % (persongroupid, personid, faceid)
    params = dict()
    headers = {
    'Content-Type' : 'application/json',
    'Ocp-Apim-Subscription-Key' : ctx.obj['apikeys']['face']
    }
    payload = json.dumps({
        'userData' : customdata or "Created %s" % str(datetime.datetime.now())
        })
    try:
        resp = requests.put(person_create_url, data=payload, params=params, headers=headers, verify=False)
        print resp
        if resp.status_code == 200:
            print "Created Person with id %s" % resp.json()['personId']
        else:
            print resp.json()['message']
    except Exception as e:
        print e

@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--persongroupid', required=True, help='The ID of the PersonGroup this person belongs to.')
@click.option('--personid', required=True, help='The ID of the PersonGroup this person belongs to.')
@click.option('--faceid', required=True, help='At least one faceid for the person.')
@click.pass_context
def retrieve_personface(ctx, persongroupid, personid, faceid):
    person_get_url = ctx.obj['oxford_url'] + '/persongroups/%s/persons/%s/faces/%s' % (persongroupid, personid, faceid)
    headers = {
    'Ocp-Apim-Subscription-Key' : ctx.obj['apikeys']['face']
    }
    try:
        resp = requests.get(person_get_url, params=None, headers=headers)
        if resp.status_code == 200:
            print json.dumps(resp.json(), sort_keys=True, indent=2, separators=(',', ': '))
        else:
            print resp.json()['message']
    except Exception as e:
        print e

@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--persongroupid', required=True, help='The ID of the PersonGroup this person belongs to.')
@click.option('--personid', required=True, help='The ID of the PersonGroup this person belongs to.')
@click.option('--faceid', required=True, help='At least one faceid for the person.')
@click.option('--customdata', default=None, help='User-provided data attached to the person group. The size limit is 16KB.')
@click.pass_context
def update_personface(ctx, persongroupid, personid, faceid, customdata):
    person_update_url = ctx.obj['oxford_url'] + '/persongroups/%s/persons/%s/faces/%s' % (persongroupid, personid, faceid)
    params = dict()
    headers = {
    'Content-Type' : 'application/json',
    'Ocp-Apim-Subscription-Key' : ctx.obj['apikeys']['face']
    }
    payload = json.dumps({
        'userData' : customdata or "Updated at %s" % str(datetime.datetime.now()),
        'faceIds' : [faceid]
        })
    try:
        resp = requests.patch(person_update_url, data=payload, params=params, headers=headers, verify=False)
        print resp
        if resp.status_code != 200:
            print resp.json()['message']
    except Exception as e:
        print e

@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--persongroupid', required=True, help='The ID of the PersonGroup this person belongs to.')
@click.option('--personid', required=True, help='The ID of the PersonGroup this person belongs to.')
@click.option('--faceid', required=True, help='At least one faceid for the person.')
@click.pass_context
def delete_personface(ctx, persongroupid, personid, faceid):
    person_delete_url = ctx.obj['oxford_url'] + '/persongroups/%s/persons/%s/faces/%s' % (persongroupid, personid, faceid)
    headers = {
    'Ocp-Apim-Subscription-Key' : ctx.obj['apikeys']['face']
    }
    try:
        resp = requests.delete(person_delete_url, params=None, headers=headers)
        if resp.status_code != 200:
            print resp.json()['message']
    except Exception as e:
        print e
   
#
# Vision commands
#
@click.group()
@click.option('--apikey', envvar='OXFORD_VISION_APIKEY', default=None, help='Your API Key from http://https://dev.projectoxford.ai/.')
@click.pass_context
def vision(ctx, apikey):
    if apikey:
        ctx.obj['apikeys']['vision'] = apikey
    ctx.obj['oxford_url'] += 'vision/v1'

@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('apikey')
@click.pass_context
def vision_api_key(ctx, apikey):
    config = load_config(CONFIG_FILE)
    config['vision'] = apikey
    save_config(CONFIG_FILE, config)
    
# use vision api to analyze an image         
@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--features', default=True, help='Optional parameter to get face landmarks.')
@click.argument('image_path', callback=resolve_input)
@click.pass_context
def analyze_image(ctx, features, image_path):
    """Analyze an image with Oxford."""
    vision_analysis_url = ctx.obj['oxford_url'] + '/analyses'
    params = {
    }
    headers = {
    'Ocp-Apim-Subscription-Key' : ctx.obj['apikeys']['vision']
    }
    if type(image_path) is file:
        headers['Content-type'] = 'application/octet-stream'
        payload = image_path.read()
    if type(image_path) is urlparse.ParseResult:
        headers['Content-type'] = 'application/json'
        payload = json.dumps({ 'Url' : image_path.geturl() })
    try:
        resp = requests.post(vision_analysis_url, params=params, data=payload, headers=headers)
        if resp.status_code == 200:
            print json.dumps(resp.json(), sort_keys=True, indent=2, separators=(',', ': '))
        else:
            print resp.json()['message']
    except Exception as e:
        print e

# use vision api to make a thumbnail         
@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--width', default=50, required=True, help='Width of thumbnail to create.')
@click.option('--height', default=50, required=True, help='Height of thumbnail to create.')
@click.option('--smartcrop/--no-smartcrop', default=True, help='Do smart cropping.')
@click.option('--thumbnail', default='thumbnail.jpg', help='Resulting thumbnail filename.')
@click.argument('image_path', callback=resolve_input)
@click.pass_context
def thumbnail(ctx, width, height, smartcrop, thumbnail, image_path):
    """Analyze an image with Oxford."""
    thumbnail_analysis_url = ctx.obj['oxford_url'] + '/thumbnails'
    params = {
        'width' : width,
        'height' : height,
        'smartCropping' : smartcrop
    }
    headers = {
    'Ocp-Apim-Subscription-Key' : ctx.obj['apikeys']['vision']
    }
    if type(image_path) is file:
        headers['Content-type'] = 'application/octet-stream'
        payload = image_path.read()
    if type(image_path) is urlparse.ParseResult:
        headers['Content-type'] = 'application/json'
        payload = json.dumps({ 'Url' : image_path.geturl() })
    try:
        resp = requests.post(thumbnail_analysis_url, params=params, data=payload, headers=headers, stream=True)
        if resp.status_code == 200:
            with open(thumbnail, 'wb') as out_file:
                shutil.copyfileobj(resp.raw, out_file)
        else:
            print resp.json()['message']
    except Exception as e:
        print e
   
# use vision api to recognize text in an image         
@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--language', default='unk', help='Language encoding in the image.')
@click.option('--detect-orientation/--no-detect-orientation', default=True, help='Detect the text orientation automatically.')
@click.argument('image_path', callback=resolve_input)
@click.pass_context
def ocr(ctx, language, detect_orientation, image_path):
    """Analyze an image with Oxford."""
    thumbnail_analysis_url = ctx.obj['oxford_url'] + '/ocr'
    params = {
        'language' : language,
        'detectOrientation' : detect_orientation
    }
    headers = {
    'Ocp-Apim-Subscription-Key' : ctx.obj['apikeys']['vision']
    }
    if type(image_path) is file:
        headers['Content-type'] = 'application/octet-stream'
        payload = image_path.read()
    if type(image_path) is urlparse.ParseResult:
        headers['Content-type'] = 'application/json'
        payload = json.dumps({ 'Url' : image_path.geturl() })
    try:
        resp = requests.post(thumbnail_analysis_url, params=params, data=payload, headers=headers, stream=True)
        if resp.status_code == 200:
            print json.dumps(resp.json(), sort_keys=True, indent=2, separators=(',', ': '))
        else:
            print resp.json()['message']
    except Exception as e:
        print e

#
# Wiring up subcommands
#

# Face
oxford.add_command(face)
face.add_command(face_api_key, name="save-api-key")
face.add_command(detect)
face.add_command(find_similar)
face.add_command(find_groups)
face.add_command(identify)

# PersonGroup
oxford.add_command(persongroup)
persongroup.add_command(create_persongroup, name="create")
persongroup.add_command(retrieve_all_persongroups, name="retrieve_all")
persongroup.add_command(retrieve_persongroup,name="retrieve")
persongroup.add_command(training_status)
persongroup.add_command(train_persongroup, name="train")
persongroup.add_command(update_persongroup, name="update")
persongroup.add_command(delete_persongroup, name="delete")
persongroup.add_command(list_people_in_persongroup, name="list_people")

# Person
oxford.add_command(person)
person.add_command(create_person, name="create")
person.add_command(retrieve_person, name="retrieve")
person.add_command(update_person, name="update")
person.add_command(delete_person, name="delete")

# PersonFace
oxford.add_command(personface)
personface.add_command(add_personface, name="add")
personface.add_command(retrieve_personface, name="retrieve")
personface.add_command(update_personface, name="update")
personface.add_command(delete_personface, name="delete")

# Vision
oxford.add_command(vision)
vision.add_command(vision_api_key, name="save-api-key")
vision.add_command(analyze_image, name="analyze")
vision.add_command(thumbnail)
vision.add_command(ocr)

if __name__ == '__main__':
    oxford(auto_envvar_prefix='OXFORD')