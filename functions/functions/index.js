const functions = require("firebase-functions");

const admin = require('firebase-admin');
admin.initializeApp();

const db = admin.firestore();

exports.notificationOnUpdate = functions.firestore
    .document('Recommendation/{userId}')
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
                newDemands.push({ 'demandId': newDemandData.demand_id, 'user_owner_id': newDemandData.user_owner_id });
            }
        });

        if (newDemands.length > 0) {
            await db.collection('Users').doc(change.after.id).collection('Notifications').doc().set({
                'name': 'Notificação de demandas recomendadas',
                'notification': newDemands.length > 1 ? `Voce tem ${newDemands.length} novas recomendações`: `Voce tem ${newDemands.length} nova recomendação`,
                'demands': newDemands,
                'type': 'recommendation'
            });
        }
    });

    exports.notificationOnCreate = functions.firestore
    .document('Recommendation/{userId}')
    .onCreate(async (snap, context) => {

        await db.collection('Users').doc(snap.id).collection('Notifications').doc().set({
            'name': 'Notificação de demandas recomendadas',
            'notification': `Voce já possui demandas recomendadas. Vá até explorar para obter algumas dicas`,
            'type': 'first_recommendation'
        });
    });