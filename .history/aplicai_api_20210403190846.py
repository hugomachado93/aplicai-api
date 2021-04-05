from flask import Flask
from flask import request
import datetime
import json
# firebase
import pandas as pd
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
# gensim
import numpy as np
import random
from tqdm import tqdm
from gensim.models import Word2Vec
import gensim.downloader as api
from gensim.models import KeyedVectors
from gensim.test.utils import common_texts
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)

cred = credentials.Certificate(
    'aplicai-firebase-adminsdk-585py-b252b67ff6.json')
firebase_admin.initialize_app(cred, {'projectId': 'aplicai'})
db = firestore.client()


def myconverter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()


def average_word2vec(skills_list, model):
    word_embeddings = []
    for skills in skills_list:
        result = average_word2vec_user_skills(skills, model, word_embeddings)
    return result


def average_word2vec_user_skills(skills, model, word_embeddings):
    avgword2vec = None
    count = 0
    for skill in skills:
        if skill in model.wv.key_to_index:
            count += 1
            if avgword2vec is None:
                avgword2vec = model.wv[skill]
            else:
                avgword2vec = avgword2vec + model.wv[skill]

        if avgword2vec is not None:
            avgword2vec = avgword2vec / count
            word_embeddings.append(avgword2vec)
    return word_embeddings

# Carrega o ultimo modelo para dar continuidade ao treinamento
@app.route("/training", methods=['GET'])
def trainning():
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

    return app.response_class(status=204, mimetype='application/json')

@app.route("/recomendation/<user_id>", methods=['GET'])
def recomend(user_id):
    #carrega o ulimo modelo salvo
    model=Word2Vec.load('skills2vec.model')
    
    #query params
    ndemands = request.args.get('ndemands', default=100, type=int)

    #query firestore
    snapshots=list(db.collection_group(u'DemandList').stream())
    user_demands_skills=list(db.collection(u'Users').document(user_id).collection(u'Demands').stream())
    user_skills=db.collection(u'Users').document(user_id).get().to_dict()['categories']

    #inicio algoritmo para pegar a n melhores demandas para o usuário
    demand_list = []
    category_list = []

    for snapshot in snapshots:
        snapshot_to_dict=snapshot.to_dict()
        snapshot_to_dict.update({'demand_id': snapshot.id})
        demand_list.append(snapshot_to_dict)
        category_list.append(snapshot_to_dict['categories'])

    average_list=average_word2vec(category_list, model)

    for snapshot in user_demands_skills:
        snapshot_to_dict=snapshot.to_dict()
        snapshot_to_dict.update({'demand_id': snapshot.id})
        user_skills = user_skills + snapshot_to_dict['categories']

    average_user = average_word2vec_user_skills(user_skills, model, [])

    result=cosine_similarity(average_user, average_list)
    
    similarities = []

    for index, demand in enumerate(demand_list):
        similarities.append([demand['demand_id'], result[0][index]])

    sorted_similarities = sorted(similarities, key= lambda x: x[1], reverse=True)

    ranked_demand_list = sorted_similarities[:ndemands]

    ranked_demands_id = [demand[0] for demand in ranked_demand_list]

    filtered_ranked_demands = []

    for demand_id in ranked_demands_id:
        for demand in demand_list:
            if demand_id == demand['demand_id']:
                filtered_ranked_demands.append(demand)

    if not user_skills:
        return app.response_class(status=204, mimetype='application/json')

    return json.dumps(filtered_ranked_demands, default=myconverter), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0')
