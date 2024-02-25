import string

from django.db import IntegrityError

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token

from business_api import models

from rest_framework.authentication import TokenAuthentication

import datetime
import json
import random
from time import sleep

import requests
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.conf import settings

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate(settings.FIREBASE_ADMIN_CERT)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://bestpay-flutter-default-rtdb.firebaseio.com'
    })

database = firestore.client()
user_collection = database.collection(u'Users')
history_collection = database.collection(u'History Web')
mail_collection = database.collection('mail')
mtn_history = database.collection('MTN_Admin_History')
mtn_tranx = mtn_history.document('mtnTransactions')
big_time = mtn_tranx.collection('big_time')
mtn_other = mtn_tranx.collection('mtnOther')
bearer_token_collection = database.collection("_KeysAndBearer")
history_web = database.collection(u'History Web').document('all_users')

totals_collection = database.collection('Totals')
admin_collection = database.collection('Admin')

class BearerTokenAuthentication(TokenAuthentication):
    keyword = 'Bearer'


def tranx_id_generator():
    file = open('business_api/counter.txt', 'r')
    content = file.read()

    tranx_id = int(content) + 1
    file = open('business_api/counter.txt', 'w')
    file.write(str(tranx_id))
    file = open('business_api/counter.txt', 'r')
    content = file.read()
    print(content)
    return content


def generate_tokenn(length):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def check_user_balance_against_price(user_id, price):
    details = get_user_details(user_id)
    wallet_balance = details['wallet']
    if wallet_balance is not None:
        return wallet_balance >= float(price)
    else:
        return None


def get_user_details(user_id):
    user = user_collection.document(user_id)
    doc = user.get()
    if doc.exists:
        doc_dict = doc.to_dict()
        print(doc_dict)
        first_name = doc_dict['first name']
        last_name = doc_dict['last name']
        email = doc_dict['email']
        phone = doc_dict['phone']
        print(first_name), print(last_name), print(email), print(phone)
        return doc.to_dict()
    else:
        return None


def send_ishare_bundle(first_name: str, last_name: str, buyer, receiver: str, email: str, bundle: float,
                       ):
    url = "https://backend.boldassure.net:445/live/api/context/business/transaction/new-transaction"

    payload = json.dumps({
        "accountNo": buyer,
        "accountFirstName": first_name,
        "accountLastName": last_name,
        "accountMsisdn": receiver,
        "accountEmail": email,
        "accountVoiceBalance": 0,
        "accountDataBalance": bundle,
        "accountCashBalance": 0,
        "active": True
    })

    token = bearer_token_collection.document("Active_API_BoldAssure")
    token_doc = token.get()
    token_doc_dict = token_doc.to_dict()
    tokennn = token_doc_dict['ishare_bearer']
    print(tokennn)

    headers = {
        'Authorization': tokennn,
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    print(response.json())
    return response


def ishare_verification(batch_id):
    if batch_id == "No batchId":
        return False

    url = f"https://backend.boldassure.net:445/live/api/context/business/airteltigo-gh/ishare/tranx-status/{batch_id}"

    payload = {}
    token = bearer_token_collection.document("Active_API_BoldAssure")
    token_doc = token.get()
    token_doc_dict = token_doc.to_dict()
    tokennn = token_doc_dict['ishare_bearer']
    headers = {
        'Authorization': tokennn
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    if response.status_code == 200:
        json_data = response.json()
        print(json_data)
        return json_data
    else:
        return False


def send_and_save_to_history(user_id, txn_type: str, txn_status: str, paid_at: str, ishare_balance: float,
                             color_code: str,
                             data_volume: float, reference: str, data_break_down: str, amount: float, receiver: str,
                             date: str, image, time: str, date_and_time: str):
    user_details = get_user_details(user_id)
    first_name = user_details['first name']
    last_name = user_details['last name']
    email = user_details['email']
    phone = user_details['phone']
    wallet = user_details['wallet']

    data = {
        'batch_id': "unknown",
        'buyer': phone,
        'color_code': color_code,
        'amount': amount,
        'data_break_down': data_break_down,
        'data_volume': data_volume,
        'date': date,
        'date_and_time': date_and_time,
        'done': "unknown",
        'email': email,
        'image': user_id,
        'ishareBalance': ishare_balance,
        'name': f"{first_name} {last_name}",
        'number': receiver,
        'paid_at': paid_at,
        'reference': reference,
        'responseCode': "0",
        'status': txn_status,
        'time': time,
        'tranxId': str(tranx_id_generator()),
        'type': txn_type,
        'uid': user_id,
        'bal': wallet
    }
    history_collection.document(date_and_time).set(data)
    history_web.collection(email).document(date_and_time).set(data)

    print("first save")

    ishare_response = send_ishare_bundle(first_name=first_name, last_name=last_name, receiver=receiver,
                                         buyer=phone,
                                         bundle=data_volume,
                                         email=email)
    json_response = ishare_response.json()
    print(f"hello:{json_response}")
    print(ishare_response.status_code)
    try:
        batch_id = json_response["batchId"]
    except KeyError:
        return ishare_response.status_code, None, email, first_name
    print(batch_id)

    doc_ref = history_collection.document(date_and_time)
    doc_ref.update({'batch_id': batch_id, 'responseCode': ishare_response.status_code})
    history_web.collection(email).document(date_and_time).update(
        {'batch_id': batch_id, 'responseCode': ishare_response.status_code})
    # data = {
    #     'batch_id': batch_id,
    #     'buyer': phone,
    #     'color_code': color_code,
    #     'amount': amount,
    #     'data_break_down': data_break_down,
    #     'data_volume': data_volume,
    #     'date': date,
    #     'date_and_time': date_and_time,
    #     'done': "unknown",
    #     'email': email,
    #     'image': image,
    #     'ishareBalance': ishare_balance,
    #     'name': f"{first_name} {last_name}",
    #     'number': receiver,
    #     'paid_at': paid_at,
    #     'reference': reference,
    #     'responseCode': status_code,
    #     'status': txn_status,
    #     'time': time,
    #     'tranxId': str(tranx_id_gen()),
    #     'type': txn_type,
    #     'uid': user_id
    # }
    # history_collection.document(date_and_time).set(data)
    # history_web.collection(email).document(date_and_time).set(data)

    print("firebase saved")
    return ishare_response.status_code, batch_id if batch_id else "No batchId", email, first_name


def big_time_transaction(receiver, date, time, date_and_time, phone, amount, data_volume, details: dict, ref,
                         channel, txn_status, user_id):
    print("==========")
    print(amount)
    data = {
        'batch_id': "unknown",
        'buyer': phone,
        'color_code': "Green",
        'amount': amount,
        'data_break_down': str(data_volume),
        'data_volume': data_volume,
        'date': date,
        'date_and_time': date_and_time,
        'done': "unknown",
        'email': details['email'],
        'image': details['user_id'],
        'ishareBalance': 0,
        'name': f"{details['first_name']} {details['last_name']}",
        'number': receiver,
        'paid_at': str(date_and_time),
        'reference': ref,
        'responseCode': 200,
        'status': txn_status,
        'time': time,
        'tranxId': str(tranx_id_generator()),
        'type': "AT Big Time",
        'uid': details['user_id']
    }
    history_collection.document(date_and_time).set(data)
    history_web.collection(details['email']).document(date_and_time).set(data)
    big_time.document(date_and_time).set(data)
    user = history_collection.document(date_and_time)
    doc = user.get()
    print(doc.to_dict())
    tranx_id = doc.to_dict()['tranxId']
    mail_doc_ref = mail_collection.document()
    file_path = 'business_api/mtn_maill.txt'  # Replace with your file path

    name = details['first_name']
    volume = data_volume
    date = date_and_time
    reference_t = ref
    receiver_t = receiver

    tot = user_collection.document(user_id)
    print(tot.get().to_dict())
    try:
        print(tot.get().to_dict()['bt_total_sales'])
        previous_sale = tot.get().to_dict()['bt_total_sales']
        print(f"Previous Sale: {previous_sale}")
        new_sale = float(previous_sale) + float(amount)
        print(new_sale)
        user_collection.document(user_id).update({'bt_total_sales': new_sale})
    except:
        user_collection.document(user_id).update({'bt_total_sales': amount})

    # previous_big_time_totals = totals_collection.document('BIGTIME TOTALS')
    # all_totals = totals_collection.document('ALL TOTALS')
    # doc = previous_big_time_totals.get()
    # doc_dict = doc.to_dict()
    #
    # previous_total_trans = doc_dict['total_trans']
    # previous_total_amount = doc_dict['total_amount']
    #
    # all_total_doc = all_totals.get()
    # all_total_doc_dict = all_total_doc.to_dict()
    #
    # previous_all_total_amount = all_total_doc_dict['total_amount']
    #
    # try:
    #     new_total_amount = previous_total_amount + amount
    # except:
    #     new_total_amount = amount
    #
    # try:
    #     new_total_trans = previous_total_trans + 1
    # except:
    #     new_total_trans = 1
    #
    # data = {
    #     'total_trans': new_total_trans,
    #     'total_amount': new_total_amount
    # }
    #
    # totals_collection.document('BIGTIME TOTALS').update(data)
    # totals_collection.document('ALL TOTALS').update({'total_amount': previous_all_total_amount + amount})

    with open(file_path, 'r') as file:
        html_content = file.read()

    placeholders = {
        '{name}': name,
        '{volume}': volume,
        '{date}': date,
        '{reference}': reference_t,
        '{receiver}': receiver_t
    }

    for placeholder, value in placeholders.items():
        html_content = html_content.replace(placeholder, str(value))

    mail_doc_ref.set({
        'to': details['email'],
        'message': {
            'subject': 'Big Time Data',
            'html': html_content,
            'messageId': 'Bestpay'
        }
    })
    return Response(data={'code': '0000', 'message': "Transaction Saved"}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([BearerTokenAuthentication])
def home(request):
    authorization_header = request.headers.get('Authorization')
    if authorization_header:
        auth_type, token = authorization_header.split(' ')
        if auth_type == 'Bearer':
            try:
                token_obj = Token.objects.get(key=token)
                user = token_obj.user
                user_details = {
                    'username': user.username,
                    'email': user.email,
                    # Add other user details as needed
                }
                return Response({'user_details': user_details, 'message': 'Welcome! You have accessed the home view.'},
                                status=status.HTTP_200_OK)
            except Token.DoesNotExist:
                return Response({'error': 'Token does not exist.'}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({'error': 'Invalid Header'})
    return Response({'error': 'Authorization header missing or invalid.'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def generate_token(request):
    username = request.data.get('username')
    user_id = request.data.get('user_id')
    full_name = request.data.get('full_name')
    email = request.data.get('email')
    if username and user_id and full_name and email:
        try:
            user = models.CustomUser.objects.create_user(username=username, user_id=user_id,
                                                         full_name=full_name, email=email)
            token_key = generate_tokenn(150)
            token = Token.objects.create(user=user, key=token_key)
            return Response({'token': token.key, 'message': 'Token Generation Successful'}, status=status.HTTP_200_OK)
        except IntegrityError:
            return Response({'message': 'User already exists!'}, status=status.HTTP_409_CONFLICT)
    else:
        return Response({'error': 'Username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def regenerate_token(request):
    user_id = request.data.get('user_id')
    try:
        user = models.CustomUser.objects.get(user_id=user_id)
        try:
            token = Token.objects.get(user=user)
            token.delete()
        except Token.DoesNotExist:
            pass

        token_key = generate_tokenn(150)
        token = Token.objects.create(user=user, key=token_key)
        return Response({'user_id': user_id, 'token': token.key, 'message': 'Token Generation Successful'},
                        status=status.HTTP_200_OK)
    except models.CustomUser.DoesNotExist:
        return Response({'error': 'User does not exist.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([BearerTokenAuthentication])
def initiate_mtn_transaction(request):
    authorization_header = request.headers.get('Authorization')
    if authorization_header:
        auth_type, token = authorization_header.split(' ')
        if auth_type == 'Bearer':
            try:
                token_obj = Token.objects.get(key=token)
                user = token_obj.user
                user_id = user.user_id

                receiver = request.data.get('receiver')
                print(receiver)
                data_volume = request.data.get('data_volume')
                print(data_volume)
                reference = request.data.get('reference')
                amount = request.data.get('amount')
                phone_number = request.data.get('phone_number')

                if not receiver or not data_volume or not reference or not amount or not phone_number:
                    return Response({'message': 'Body parameters not valid. Check and try again.'},
                                    status=status.HTTP_400_BAD_REQUEST)

                prices_dict = {
                    1000: 3.9,
                    2000: 7.8,
                    3000: 11,
                    4000: 14.5,
                    5000: 18,
                    6000: 21,
                    7000: 24.5,
                    8000: 27,
                    10000: 32,
                    15000: 48,
                    20000: 64,
                    25000: 78,
                    30000: 94,
                    40000: 128,
                    50000: 155,
                    100000: 290
                }

                amount_to_be_deducted = prices_dict[data_volume]
                print(str(amount_to_be_deducted) + "================")
                channel = phone_number
                date = datetime.datetime.now().strftime("%a, %b %d, %Y")
                time = datetime.datetime.now().strftime("%I:%M:%S %p")
                date_and_time = datetime.datetime.now().isoformat()
                if "wallet" == "wallet":
                    print("used this")
                    try:
                        enough_balance = check_user_balance_against_price(user_id, amount_to_be_deducted)
                    except:
                        return Response(
                            {'code': '0001', 'message': f'User ID does not exist: User ID provided: {user_id}.'},
                            status=status.HTTP_400_BAD_REQUEST)
                else:
                    enough_balance = True
                    print("not wallet")
                print(enough_balance)
                if enough_balance:
                    user_details = get_user_details(user_id)
                    first_name = user_details['first name']
                    last_name = user_details['last name']
                    email = user_details['email']
                    phone = user_details['phone']
                    bal = user_details['wallet']
                    # hist = history_web.collection(email).document(date_and_time)
                    # doc = hist.get()
                    # if doc.exists:
                    #     print(doc)
                    #     return redirect(f"https://{callback_url}")
                    # else:
                    #     print("no record found")
                    if "wallet" == "wallet":
                        print("updated")
                        user = get_user_details(user_id)
                        if user is None:
                            return None
                        previous_user_wallet = user['wallet']
                        print(f"previous wallet: {previous_user_wallet}")
                        new_balance = float(previous_user_wallet) - float(amount_to_be_deducted)
                        print(f"new_balance:{new_balance}")
                        doc_ref = user_collection.document(user_id)
                        doc_ref.update({'wallet': new_balance})
                        user = get_user_details(user_id)
                        new_user_wallet = user['wallet']
                        print(f"new_user_wallet: {new_user_wallet}")
                        if new_user_wallet == previous_user_wallet:
                            user = get_user_details(user_id)
                            if user is None:
                                return None
                            previous_user_wallet = user['wallet']
                            print(f"previous wallet: {previous_user_wallet}")
                            new_balance = float(previous_user_wallet) - float(amount_to_be_deducted)
                            print(f"new_balance:{new_balance}")
                            doc_ref = user_collection.document(user_id)
                            doc_ref.update({'wallet': new_balance})
                            user = get_user_details(user_id)
                            new_user_wallet = user['wallet']
                            print(f"new_user_wallet: {new_user_wallet}")
                        else:
                            print("it's fine")

                    data = {
                        'batch_id': "unknown",
                        'buyer': channel,
                        'color_code': "Green",
                        'amount': amount_to_be_deducted,
                        'data_break_down': data_volume,
                        'data_volume': data_volume,
                        'date': str(date),
                        'date_and_time': str(date_and_time),
                        'done': "unknown",
                        'email': email,
                        'image': user_id,
                        'ishareBalance': '',
                        'name': f"{first_name} {last_name}",
                        'number': receiver,
                        'paid_at': str(date_and_time),
                        'reference': reference,
                        'responseCode': 200,
                        'status': "Undelivered",
                        'bal': bal,
                        'time': str(time),
                        'tranxId': str(tranx_id_generator()),
                        'type': "MTN Master Bundle",
                        'uid': user_id
                    }

                    history_collection.document(date_and_time).set(data)
                    history_web.collection(email).document(date_and_time).set(data)
                    user = history_collection.document(date_and_time)
                    doc = user.get()
                    print(doc.to_dict())
                    tranx_id = doc.to_dict()['tranxId']
                    second_data = {
                        'amount': amount_to_be_deducted,
                        'batch_id': "unknown",
                        'channel': "wallet",
                        'color_code': "Green",
                        'created_at': date_and_time,
                        'data_volume': data_volume,
                        'date': str(date),
                        'email': email,
                        'date_and_time': date_and_time,
                        'image': user_id,
                        'ip_address': "",
                        'ishareBalance': 0,
                        'name': f"{first_name} {last_name}",
                        'number': receiver,
                        'buyer': channel,
                        'paid_at': date_and_time,
                        'payment_status': "success",
                        'reference': reference,
                        'status': "Undelivered",
                        'bal': bal,
                        'time': str(time),
                        'tranxId': tranx_id,
                        'type': "MTN Master Bundle"
                    }
                    mtn_other.document(date_and_time).set(second_data)
                    print("pu")

                    tot = user_collection.document(user_id)
                    print(tot.get().to_dict())
                    try:
                        print(tot.get().to_dict()['mtn_total_sales'])
                        previous_sale = tot.get().to_dict()['mtn_total_sales']
                        print(f"Previous Sale: {previous_sale}")
                        new_sale = float(previous_sale) + float(amount)
                        print(new_sale)
                        user_collection.document(user_id).update({'mtn_total_sales': new_sale})
                    except:
                        user_collection.document(user_id).update({'mtn_total_sales': amount})

                    mail_doc_ref = mail_collection.document()
                    file_path = 'business_api/mtn_maill.txt'  # Replace with your file path

                    name = first_name
                    volume = data_volume
                    date = date_and_time
                    reference_t = reference
                    receiver_t = receiver

                    with open(file_path, 'r') as file:
                        html_content = file.read()

                    placeholders = {
                        '{name}': name,
                        '{volume}': volume,
                        '{date}': date,
                        '{reference}': reference_t,
                        '{receiver}': receiver_t
                    }

                    for placeholder, value in placeholders.items():
                        html_content = html_content.replace(placeholder, str(value))

                    mail_doc_ref.set({
                        'to': email,
                        'message': {
                            'subject': 'MTN Data',
                            'html': html_content,
                            'messageId': 'Bestpay'
                        }
                    })
                    print("got to redirect")
                    return Response(data={"status": "200", "message": "Transaction received successfully"},
                                    status=status.HTTP_200_OK)
                else:
                    return Response({"status": '400', 'message': 'Not enough balance to perform transaction'},
                                    status=status.HTTP_400_BAD_REQUEST)
            except Token.DoesNotExist:
                return Response({'error': 'Token does not exist.'}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({'error': 'Invalid Header Provided.'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([BearerTokenAuthentication])
def initiate_ishare_transaction(request):
    authorization_header = request.headers.get('Authorization')
    if authorization_header:
        auth_type, token = authorization_header.split(' ')
        if auth_type == 'Bearer':
            try:

                receiver = request.data.get('receiver')
                print(receiver)
                data_volume = request.data.get('data_volume')
                print(data_volume)
                reference = request.data.get('reference')
                amount = request.data.get('amount')
                phone_number = request.data.get('phone_number')
                channel = request.data.get('channel')
                txn_type = request.data.get('txn_type')
                txn_status = request.data.get('txn_status')
                paid_at = request.data.get('paid_at')
                ishare_balance = request.data.get('ishare_balance')
                color_code = request.data.get('color_code')
                data_break_down = request.data.get('data_break_down')
                image = request.data.get('image')

                if not receiver or not data_volume or not reference or not amount or not phone_number or not channel or not txn_type or not txn_status or not paid_at or not ishare_balance or not color_code or not data_break_down or not image:
                    return Response({'message': 'Body parameters not valid. Check and try again.'},
                                    status=status.HTTP_400_BAD_REQUEST)

                token_obj = Token.objects.get(key=token)
                user = token_obj.user
                user_id = user.user_id

                date = datetime.datetime.now().strftime("%a, %b %d, %Y")
                time = datetime.datetime.now().strftime("%I:%M:%S %p")
                date_and_time = datetime.datetime.now().isoformat()

                if channel.lower() == "wallet":
                    try:
                        enough_balance = check_user_balance_against_price(user_id, amount)
                    except:
                        return Response(
                            {'code': '0001', 'message': f'User ID does not exist: User ID provided: {user_id}.'},
                            status=status.HTTP_400_BAD_REQUEST)
                else:
                    enough_balance = True
                    print("not wallet")
                print(enough_balance)
                if enough_balance:
                    user_details = get_user_details(user_id)
                    email = user_details['email']
                    print(enough_balance)
                    # hist = history_web.collection(email).document(date_and_time)
                    # doc = hist.get()
                    # if doc.exists:
                    #     return redirect(f"https://{callback_url}")
                    # else:
                    #     print("no record found")
                    if channel.lower() == "wallet":
                        user = get_user_details(user_id)
                        if user is None:
                            return None
                        previous_user_wallet = user['wallet']
                        print(f"previous wallet: {previous_user_wallet}")
                        new_balance = float(previous_user_wallet) - float(amount)
                        print(f"new_balance:{new_balance}")
                        doc_ref = user_collection.document(user_id)
                        doc_ref.update({'wallet': new_balance})
                        user = get_user_details(user_id)
                        new_user_wallet = user['wallet']
                        print(f"new_user_wallet: {new_user_wallet}")
                        if new_user_wallet == previous_user_wallet:
                            user = get_user_details(user_id)
                            if user is None:
                                return None
                            previous_user_wallet = user['wallet']
                            print(f"previous wallet: {previous_user_wallet}")
                            new_balance = float(previous_user_wallet) - float(amount)
                            print(f"new_balance:{new_balance}")
                            doc_ref = user_collection.document(user_id)
                            doc_ref.update({'wallet': new_balance})
                            user = get_user_details(user_id)
                            new_user_wallet = user['wallet']
                            print(f"new_user_wallet: {new_user_wallet}")
                        else:
                            print("it's fine")
                    status_code, batch_id, email, first_name = send_and_save_to_history(user_id, txn_type, txn_status,
                                                                                        paid_at,
                                                                                        float(ishare_balance),
                                                                                        color_code, float(data_volume),
                                                                                        reference,
                                                                                        data_break_down,
                                                                                        float(amount), receiver,
                                                                                        date, image, time,
                                                                                        date_and_time)
                    print(status_code)
                    print(batch_id)
                    if batch_id is None:
                        return Response(data={'status_code': status_code, "message": "Transaction Failed"},
                                        status=status.HTTP_400_BAD_REQUEST)
                    sleep(10)
                    ishare_verification_response = ishare_verification(batch_id)
                    if ishare_verification_response is not False:
                        code = \
                            ishare_verification_response["flexiIshareTranxStatus"]["flexiIshareTranxStatusResult"][
                                "apiResponse"][
                                "responseCode"]
                        ishare_response = \
                            ishare_verification_response["flexiIshareTranxStatus"]["flexiIshareTranxStatusResult"][
                                "ishareApiResponseData"][
                                "apiResponseData"][
                                0][
                                "responseMsg"]
                        print(code)
                        print(ishare_response)
                        if code == '200' or ishare_response == 'Crediting Successful.':
                            sms = f"Hey there\nYour account has been credited with {data_volume}MB.\nConfirm your new balance using the AT Mobile App"
                            r_sms_url = f"https://sms.arkesel.com/sms/api?action=send-sms&api_key=UmpEc1JzeFV4cERKTWxUWktqZEs&to={receiver}&from=Bestpay&sms={sms}"
                            response = requests.request("GET", url=r_sms_url)
                            print(response.text)
                            doc_ref = history_collection.document(date_and_time)
                            doc_ref.update({'done': 'Successful'})
                            mail_doc_ref = mail_collection.document(f"{batch_id}-Mail")
                            file_path = 'business_api/mail.txt'  # Replace with your file path

                            name = first_name
                            volume = data_volume
                            date = date_and_time
                            reference_t = reference
                            receiver_t = receiver

                            with open(file_path, 'r') as file:
                                html_content = file.read()

                            placeholders = {
                                '{name}': name,
                                '{volume}': volume,
                                '{date}': date,
                                '{reference}': reference_t,
                                '{receiver}': receiver_t
                            }

                            for placeholder, value in placeholders.items():
                                html_content = html_content.replace(placeholder, str(value))

                            mail_doc_ref.set({
                                'to': email,
                                'message': {
                                    'subject': 'AT Flexi Bundle',
                                    'html': html_content,
                                    'messageId': 'Bestpay'
                                }
                            })

                            tot = user_collection.document(user_id)
                            print(tot.get().to_dict())
                            try:
                                print(tot.get().to_dict()['at_total_sales'])
                                previous_sale = tot.get().to_dict()['at_total_sales']
                                print(f"Previous Sale: {previous_sale}")
                                new_sale = float(previous_sale) + float(amount)
                                print(new_sale)
                                user_collection.document(user_id).update({'at_total_sales': new_sale})
                            except:
                                user_collection.document(user_id).update({'at_total_sales': amount})

                            return Response(data={'status_code': status_code, 'batch_id': batch_id},
                                            status=status.HTTP_200_OK)
                        else:
                            doc_ref = history_collection.document(date_and_time)
                            doc_ref.update({'done': 'Failed'})
                            return Response(data={'status_code': status_code, "message": "Transaction Failed"},
                                            status=status.HTTP_400_BAD_REQUEST)
                    else:
                        return Response(data={'status_code': status_code, "message": "Could not verify transaction"},
                                        status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response(data={'status_code': 400, "message": "Not enough balance"},
                                    status=status.HTTP_400_BAD_REQUEST)
            except Token.DoesNotExist:
                return Response({'error': 'Token does not exist.'}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({'error': 'Invalid Header Provided.'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def get_user_token(request):
    user_id = request.data.get('user_id')
    if user_id:
        try:
            user = models.CustomUser.objects.get(user_id=user_id)
            token = Token.objects.get(user=user)
            return Response({'user_id': user_id, 'token': token.key}, status=status.HTTP_200_OK)
        except models.CustomUser.DoesNotExist:
            return Response({'message': 'User does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        except Token.DoesNotExist:
            return Response({'message': 'Token does not exist for the user.'}, status=status.HTTP_404_NOT_FOUND)
    else:
        return Response({'message': 'User ID parameter is missing.'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([BearerTokenAuthentication])
def initiate_big_time(request):
    authorization_header = request.headers.get('Authorization')
    if authorization_header:
        auth_type, token = authorization_header.split(' ')
        if auth_type == 'Bearer':
            try:
                token_obj = Token.objects.get(key=token)
                user = token_obj.user
                user_id = user.user_id
                print(user_id)

                print("hiiiii")

                receiver = request.data.get('receiver')
                data_volume = request.data.get('data_volume')
                reference = request.data.get('reference')
                amount = request.data.get('amount')
                print(amount)
                phone_number = request.data.get('phone_number')

                print("yo")

                if not receiver or not data_volume or not reference or not amount or not phone_number:
                    return Response({'message': 'Body parameters not valid. Check and try again.'},
                                    status=status.HTTP_400_BAD_REQUEST)

                print("got here")
                user_details = get_user_details(user_id)
                print(user_details['first name'])

                date = datetime.datetime.now().strftime("%a, %b %d, %Y")
                time = datetime.datetime.now().strftime("%I:%M:%S %p")
                date_and_time = datetime.datetime.now().isoformat()

                if user_details is not None:
                    print("yes")
                    first_name = user_details['first name']
                    print(first_name)
                    last_name = user_details['last name']
                    print(last_name)
                    email = user_details['email']
                    phone = user_details['phone']
                else:
                    first_name = ""
                    last_name = ""
                    email = ""
                    phone = ""
                details = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'user_id': user_id
                }
                big_time_response = big_time_transaction(receiver=receiver, date_and_time=date_and_time, date=date,
                                                         time=time, amount=amount, data_volume=data_volume,
                                                         channel="MoMo", phone=phone, ref=reference,
                                                         details=details, txn_status="Undelivered", user_id=user_id)
                if big_time_response.status_code == 200 or big_time_response.data["code"] == "0000":
                    return Response(data={"status": "200", "message": "Transaction received successfully"},
                                    status=status.HTTP_200_OK)
                else:
                    return Response({"status": '400', 'message': 'Something went wrong'},
                                    status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                print(e)
                return Response({"status": '400', 'message': f'Something went wrong: {e}'},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'error': 'Invalid Header Provided.'}, status=status.HTTP_401_UNAUTHORIZED)
    else:
        return Response({'error': 'Invalid Header Provided.'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([BearerTokenAuthentication])
def wallet_topup(request):
    authorization_header = request.headers.get('Authorization')
    if authorization_header:
        auth_type, token = authorization_header.split(' ')
        if auth_type == 'Bearer':
            try:
                token_obj = Token.objects.get(key=token)
                user = token_obj.user
                user_id = user.user_id

                amount = request.data.get('topup_amount')
                reference = request.data.get('reference')

                if not amount or not reference:
                    return Response({'message': 'Body parameters not valid. Check and try again.'},
                                    status=status.HTTP_400_BAD_REQUEST)

                date = datetime.datetime.now().strftime("%a, %b %d, %Y")
                time = datetime.datetime.now().strftime("%I:%M:%S %p")
                date_and_time = datetime.datetime.now().isoformat()

                user_details = get_user_details(user_id)
                if user_details is not None:
                    print(user_details)
                    first_name = user_details['first name']
                    last_name = user_details['last name']
                    email = user_details['email']
                    phone = user_details['phone']
                    try:
                        previous_wallet = user_details['wallet']
                    except KeyError:
                        previous_wallet = 0
                else:
                    first_name = ""
                    last_name = ""
                    email = ""
                    phone = ""
                    previous_wallet = 0
                all_data = {
                    'batch_id': "unknown",
                    'buyer': phone,
                    'color_code': "Green",
                    'amount': amount,
                    'data_break_down': amount,
                    'data_volume': amount,
                    'date': date,
                    'date_and_time': date_and_time,
                    'done': "Success",
                    'email': email,
                    'image': user_id,
                    'ishareBalance': 0,
                    'name': f"{first_name} {last_name}",
                    'number': phone,
                    'paid_at': date_and_time,
                    'reference': reference,
                    'responseCode': 200,
                    'status': "Credited",
                    'time': time,
                    'tranxId': str(tranx_id_generator()),
                    'type': "WALLETTOPUP",
                    'uid': user_id
                }
                history_web.collection(email).document(date_and_time).set(all_data)
                print("f saved")
                history_collection.document(date_and_time).set(all_data)
                print(f"ya{history_collection.document(date_and_time).get().to_dict()}")
                print("f saved")
                print(f"yo{history_web.collection(email).document(date_and_time).get().to_dict()}")
                to_be_added = float(amount)
                print(f"amount to be added: {to_be_added}")
                new_balance = previous_wallet + to_be_added
                print(f" new balance: {new_balance}")
                doc_ref = user_collection.document(user_id)
                doc_ref.update(
                    {'wallet': new_balance, 'wallet_last_update': date_and_time,
                     'recent_wallet_reference': reference})
                print(doc_ref.get().to_dict())
                print("before all data")
                all_data = {
                    'batch_id': "unknown",
                    'buyer': phone,
                    'color_code': "Green",
                    'amount': amount,
                    'data_break_down': amount,
                    'data_volume': amount,
                    'date': date,
                    'date_and_time': date_and_time,
                    'done': "Success",
                    'email': email,
                    'image': user_id,
                    'ishareBalance': 0,
                    'name': f"{first_name} {last_name}",
                    'number': phone,
                    'paid_at': date_and_time,
                    'reference': reference,
                    'responseCode': 200,
                    'status': "Credited",
                    'time': time,
                    'tranxId': str(tranx_id_generator()),
                    'type': "WALLETTOPUP",
                    'uid': user_id
                }
                history_web.collection(email).document(date_and_time).set(all_data)
                print("saved")
                history_collection.document(date_and_time).set(all_data)
                print(f"ya{history_collection.document(date_and_time).get().to_dict()}")
                print("saved")
                print(f"yo{history_web.collection(email).document(date_and_time).get().to_dict()}")

                name = f"{first_name} {last_name}"
                amount = to_be_added
                file_path = 'business_api/wallet_mail.txt'
                mail_doc_ref = mail_collection.document()

                with open(file_path, 'r') as file:
                    html_content = file.read()

                placeholders = {
                    '{name}': name,
                    '{amount}': amount
                }

                for placeholder, value in placeholders.items():
                    html_content = html_content.replace(placeholder, str(value))

                mail_doc_ref.set({
                    'to': email,
                    'message': {
                        'subject': 'Wallet Topup',
                        'html': html_content,
                        'messageId': 'Bestpay'
                    }
                })

                sms_message = f"GHS {to_be_added} was deposited in your wallet. Available balance is now GHS {new_balance}"
                sms_url = f"https://sms.arkesel.com/sms/api?action=send-sms&api_key=UmpEc1JzeFV4cERKTWxUWktqZEs&to=0{user_details['phone']}&from=Bestpay&sms={sms_message}"
                response = requests.request("GET", url=sms_url)
                print(response.status_code)
                return Response(data={"status": "200", "message": "Wallet Topup Successful"},
                                status=status.HTTP_200_OK)
            except Token.DoesNotExist or models.CustomUser.DoesNotExist:
                return Response({'error': 'Token does not exist.'}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({'error': 'Invalid Header Provided.'}, status=status.HTTP_401_UNAUTHORIZED)
