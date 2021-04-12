from flask import Flask
from flask import request
import datetime
import json
import pandas as pd
# firebase
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from firebase_admin import storage
# gensim
import numpy as np
import random
from tqdm import tqdm
from gensim.models import Word2Vec
import gensim.downloader as api
from gensim.models import KeyedVectors
from gensim.test.utils import common_texts
from sklearn.metrics.pairwise import cosine_similarity
from gensim.similarities import WmdSimilarity
from itertools import chain

app = Flask(__name__)

cred = credentials.Certificate(
    'aplicai-firebase-adminsdk-585py-b252b67ff6.json')
firebase_admin.initialize_app(cred, {'projectId': 'aplicai', 'storageBucket': 'aplicai.appspot.com'})
db = firestore.client()

def myconverter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()

# Carrega o ultimo modelo para dar continuidade ao treinamento
@app.route("/trainning", methods=['GET'])
def trainning():
    blob_download = storage.bucket().blob('word2vec_model/skills2vec.model')
    blob_download.download_to_filename('skills2vec.model')
    blob_upload = storage.bucket().blob('word2vec_model/skills2vec.model')
    model=Word2Vec.load('skills2vec.model')
    snapshots=list(db.collection_group(u'Demands').stream())
    demand_list=[]
    categories_list=[]

    for snapshot in snapshots:
        snapshot_to_dict=snapshot.to_dict()
        snapshot_to_dict.update({'demand_id': snapshot.id})
        demand_list.append(snapshot_to_dict)
        categories_list.append(snapshot_to_dict['categories'])

    model.train(categories_list, total_examples=len(categories_list), epochs=model.epochs)
    model.save('skills2vec.model')
    blob_upload.upload_from_filename('skills2vec.model')

    return app.response_class(status=204, mimetype='application/json')

@app.route("/offline-recommendation", methods=['GET'])    
def recomendv2():
    #carrega o ulimo modelo salvo
    model=Word2Vec.load('skills2vec.model')
    
    #query params
    ndemands = request.args.get('ndemands', default=100, type=int)

    #query firestore
    snapshots=list(db.collection_group(u'DemandList').stream())

    #inicio algoritmo para pegar a n melhores demandas para cada usuário
    demand_list = []
    category_list = []

    #pega todas as demandas
    for snapshot in snapshots:
        snapshot_to_dict=snapshot.to_dict()
        snapshot_to_dict.update({'demand_id': snapshot.id, 'user_owner_id': str(snapshot.reference.parent.parent.id)})
        demand_list.append(snapshot_to_dict)
        category_list.append([skill.lower() for skill in snapshot_to_dict['categories']])

    #Pega as skills para cada usuario
    snapshots = list(db.collection(u'Users').where(u'isFinished', u'==', True).where(u'type', u'==', 'student').stream())
    user_list = []
    user_skills_list = []
    for snapshot in snapshots:
        snapshot_to_dict = snapshot.to_dict()
        snapshot_to_dict.update({'user_id': snapshot.id})
        user_list.append(snapshot_to_dict)
        user_skills_list.append([skill.lower() for skill in snapshot_to_dict['categories']])

    user_demand_list = []
    user_demands_skills_list = []
    for user in user_list:
        snapshots = list(db.collection(u'Users').document(user['user_id']).collection(u'Demands').stream())
        demand_temp_list = []
        skills_list = []
        for snapshot in snapshots:
            snapshot_to_dict = snapshot.to_dict()
            snapshot_to_dict.update({'demand_id': snapshot.id})
            demand_temp_list.append(snapshot_to_dict)
            skills_list.append([skill.lower() for skill in snapshot_to_dict['categories']])
        user_demand_list.append(demand_temp_list)
        user_demands_skills_list.append(list(chain.from_iterable(skills_list)))

    user_joined_perfil_demand_skills = []
    for index in range(len(user_skills_list)):
        user_joined_perfil_demand_skills.append(list(set(user_skills_list[index] + user_demands_skills_list[index])))
    ndemands

    demands_sim_list = []
    for index, user_skills in enumerate(user_joined_perfil_demand_skills):
        instance = WmdSimilarity(category_list, model.wv, num_best=ndemands)
        sims = instance[user_skills]
        demands_sim_list.append(sims)

    for index, demand_sim in enumerate(demands_sim_list):
        recomend_list = []
        for sim in demand_sim:
            recomend_list.append({'demand_id': demand_list[sim[0]]['demand_id'], 'user_owner_id': demand_list[sim[0]]['user_owner_id'], 'similarity': sim[1]})
        recomend_dict = {'recomended_demand': recomend_list}
        db.collection('Recomendation').document(user_list[index]['user_id']).set(recomend_dict)

    return app.response_class(status=204, mimetype='application/json')

if __name__ == "__main__":
    app.run(host='0.0.0.0')