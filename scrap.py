from ast import parse
from email.mime import base
from os import curdir, spawnlp
from unicodedata import name
from bs4 import BeautifulSoup
from openpecha.core.ids import get_pecha_id
from openpecha.core.pecha import OpenPechaFS
from openpecha.core.layer import InitialCreationEnum, Layer, LayerEnum, PechaMetaData
from openpecha.core.annotation import Page, Span
from datetime import datetime
import requests
import re
from uuid import uuid4




def make_request(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text,'lxml')
    return soup


def parse_home_page(url):
    page = make_request(url)
    links = page.select("ul#navigation > li > a")
    for link in links:
        if re.search("tenjur|kangyur",link.text,re.IGNORECASE):
            parse_link_page(link['href'])


def parse_link_page(link):
    page = make_request(link)
    table = page.find('table',{'style':'position:relative;left:20px'})
    links = table.find_all("a")
    for link in links:
        if re.search("text",link.text,re.IGNORECASE):
            parse_text_page(link['href'])


def parse_text_page(url):
    pecha_id = get_pecha_id()
    page=make_request(url)
    table = page.find('table',{'style':'position:relative;left:20px'})
    links = table.find_all("a")
    for link in links:
        if re.search("^.*\.(txt)$",link['href']):
            span = link.find_next_sibling()
            filename = get_file_name(span.text,"^.*(\d+)\.(txt).*")
            text_with_imgnum,clean_text = get_base_text(link)
            create_opf(pecha_id=pecha_id,filename=filename,text_with_imgnum=text_with_imgnum,clean_text=clean_text)
            
    print("DONE")


def parse_tengyur_page(url):
    page = make_request(url)
    table = page.find('table',{'style':'position:relative;left:20px'})
    links = table.find_all("a")
    pecha_id = get_pecha_id()
    vol_no = 1
    vol_no_title = {}
    for link in links:
        page = make_request(link['href'])
        table = page.find('table',{'style':'position:relative;left:20px'})
        links = table.find_all("a")
        for link in links:
            span = link.find_next_sibling()
            filename = get_file_name(span.text,"(.*)\.(txt).*")
            vol_no_title.update({vol_no:filename})
            clean_text = get_base_text(link)
            create_opf(clean_text=clean_text,filename=vol_no,pecha_id=pecha_id)
            vol_no+=1

    create_meta(pecha_id,vol_no_title)


def create_meta(pecha_id,vol_no_title):
    opf_path=f"./opfs/{pecha_id}/{pecha_id}.opf"
    opf= OpenPechaFS(opf_path=opf_path)

    instance_meta = PechaMetaData(
        initial_creation_type=InitialCreationEnum.input,
        created_at=datetime.now(),
        last_modified_at=datetime.now(),
        source_metadata={"volume_no_to_title":vol_no_title})

    meta = instance_meta 
    opf._meta=meta
    opf.save_meta()

def get_file_name(filename,pattern):
    filename =  re.search(pattern,filename)    
    return filename.group(1)


def get_base_text(link):
    page = requests.get(link['href'])
    soup = BeautifulSoup(page.content,'lxml')
    div = soup.find('div',{'style':'width:890px; position:relative; left:120px;top:40px;'})
    text = div.get_text()
    if re.search("\{འཀའ་འགྱུར།_(\d+)\}",text):
        text_with_imgnum,clean_text = extract_imgnum(text.strip("\n"))
        return text_with_imgnum,clean_text
    else:
        return text


def extract_imgnum(text):
    texts = re.split("\{འཀའ་འགྱུར།_.*\}",text)
    imgnums = re.findall("\{འཀའ་འགྱུར།_(\d+)\}",text)
    text_with_imgnum = []
    clean_text = ""
    for text,imgnum in zip(texts,imgnums):
        if text == "":
            continue
        if text == "\n":
            text_with_imgnum.append({'text':'','imgnum':imgnum})
            continue
        
        text = remove_endlines(text)
        text_with_imgnum.append({'text':text,'imgnum':imgnum})
        clean_text+=text+"\n\n\n"
    
    return text_with_imgnum,clean_text


def remove_endlines(text):
    prev = ''
    while prev != text.strip("\n"):
        prev =text.strip("\n")

    return prev    


def create_opf(**kwargs):
    opf_path = f"./opfs/{kwargs['pecha_id']}/{kwargs['pecha_id']}.opf"
    opf = OpenPechaFS(opf_path=opf_path)
    filename  = str("{:0>3d}".format(int(kwargs['filename'])))
    bases = {f"v{filename}":kwargs['clean_text']}
    if "text_with_imgnum" in kwargs:
        layers = {f"v{filename}": {LayerEnum.pagination: get_pagination_layer(kwargs['text_with_imgnum'])}}
        opf.layers = layers
        opf.save_layers()

    opf.base = bases
    opf.save_base()


def get_pagination_layer(text_with_imgnum):
    page_annotations = {}
    char_walker = 0

    for text in text_with_imgnum:
        page_annotation, char_walker,text = get_page_annotation(text, char_walker)
        page_annotations.update(page_annotation)

    pagination_layer = Layer(
        annotation_type=LayerEnum.pagination, annotations=page_annotations
    )

    return pagination_layer


def get_page_annotation(text,char_walker):
    #imgnum = re.search('[^0]*0+(\d+)$',text['imgnum']).group(1)
    imgnum = text['imgnum']
    text = text['text']

    page_annotation = {
        uuid4().hex: Page(span=Span(start=char_walker, end=char_walker+len(text)), imgnum=imgnum)
    } 

    return page_annotation,(char_walker + len(text) + 3),text  
    

def main():
    url = "https://www.buddism.ru///CANON/_TENJUR_MAIN/TENGYUR_UNI_clean14_12_09/"
    #parse_home_page(url)
    parse_tengyur_page(url)

    
if __name__ == "__main__":
    main()


