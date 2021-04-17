const functions = require("firebase-functions");

// The Firebase Admin SDK to access Firestore.
const admin = require('firebase-admin');
admin.initializeApp();

const db = admin.firestore();

exports.notificationHandler = functions.firestore
    .document('Recomendation/{userId}')
    .onUpdate(async (change, context) => {

        const data = change.after.data();
        const previousData = change.before.data();

        const newDemands = [];

        data.recomended_demand.forEach((newElement) => {
            let newDemandData = newElement;
            previousData.recomended_demand.forEach((previousElement) => {
                if (newElement.demand_id === previousElement.demand_id) {
                    newDemandData = null;
                }
            });
            if (newDemandData !== null) {
                newDemands.push({'demandId': newDemandData.demand_id, 'user_owner_id': newDemandData.user_owner_id});
            }
        });

        const newRecomendations = data.recomended_demand.length - unchangedDemands;

        if (newDemands.length > 0) {
            await db.collection('Users').doc(change.after.id).collection('Notifications').doc().set({
                'name': 'Notificação de demandas recomendadas',
                'notification': `Voce tem ${newRecomendations} novas recomendações`,
                'demands': newDemands,
                'type': 'recomendation'
            });
        }
    });