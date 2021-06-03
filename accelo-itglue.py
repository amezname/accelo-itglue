import requests, json, re, datetime
from requests.exceptions import HTTPError
import config as cfg


#Authentication and Token Creation

url = f"https://{cfg.deployment}/oauth2/v0/token?grant_type=client_credentials&scope=read(all)&expires_in=3600"

payload={}
headers = {
	'Content-Transfer-Encoding': 'application/x-www-form-urlencoded',
	'Authorization': f'Basic {cfg.acc_credentials}'
}

auth = requests.request("POST", url, headers=headers, data=payload).json()
token = auth['access_token']

itg_headers = {
  		'x-api-key': cfg.api_key
  	}

#Functions
def logger(message):
	file = cfg.filepath
	now = datetime.datetime.now()
	logtime = str(now)
	with open(file, "a") as log:
		log.write(logtime + "   " + message + "\n")

def get_acc(token, url):

	payload = {}
	headers = {
		'Authorization': 'Bearer ' + token
	}
	try:
		response = requests.request("GET", url, headers=headers, data=payload)
		response.raise_for_status()	
	except HTTPError as http_err:
		logger(f"HTTP Error occurred: {http_err}")
		logger(f"{http_err.response.text}")
	except Exception as err:
		logger(f"Other error occurred: {err}")
	else:
		r = response.json()
		return r
	

def get_itg(url,headers):

	payload={}
	try:
		response = requests.request("GET", url, headers=headers, data=payload)
		response.raise_for_status()
	except HTTPError as http_err:
		logger(f"HTTP Error occurred: {http_err}")
		logger(f"{http_err.response.text}")
	except Exception as err:
		logger(f"Other error occurred: {err}")
	else:
		r = response.json()
		return r
	

def patch(url,headers,payload):
	
	first = payload['data']['attributes']['first_name']
	last = payload['data']['attributes']['last_name']
	
	try:
		response = requests.request("PATCH",url, headers=headers, data=json.dumps(payload))
		response.raise_for_status()
	except HTTPError as http_err:
		logger(f"HTTP Error occurred: {http_err}")
		logger(f"{http_err.response.text}")
		logger(f"Contact {first} {last} not updated.")
	except Exception as err:
		logger(f"Other error occurred: {err}")
		logger(f"Contact {first} {last} not updated.")
	else:
		return response
	

def post(url,headers,payload):

	first = payload['data']['attributes']['first_name']
	last = payload['data']['attributes']['last_name']
	
	try:
		response = requests.request("POST",url, headers=headers, data=json.dumps(payload))
		response.raise_for_status()
	except HTTPError as http_err:
		logger(f"HTTP Error occurred: {http_err}")
		logger(f"{http_err.response.text}")
		logger(f"Contact {first} {last} not created.")
	except Exception as err:
		logger(f"Other error occurred: {err}")
		logger(f"Contact {first} {last} not created.")
	else:
		return response
	


#Retrieve all active companies from accelo
try:
	active_comps = get_acc(token, f"https://{cfg.deployment}/api/v0/companies?_filters=status(3)&_limit=100")['response']

except: 
	logger("Error retrieving active companies from Accelo")

#Retrive all contacts for each company from accelo
else: 
	eid = active_comps[13]['id']
	organization = active_comps[13]['name']
	print(organization)

	try: 
		# Gets up to 100 contacts for each organization. Additional fields can be added.
		contacts = get_acc(token, f'https://{cfg.deployment}/api/v0/companies/{eid}/contacts?_fields=phone, position, standing, physical_address(title)&_limit=100')['response']

	except: 
		logger(f"Error retrieving contacts for {organization}")

	else:
		#Retrieve organization id from it glue based off name. Company name in Accelo must match organization in IT Glue

		try: 
			org_id = get_itg(f"https://api.itglue.com/organizations?filter[name]={organization}",itg_headers)['data'][0]['id']
			print(f"Organization Id: {org_id}")

		except: 
			logger(f"Could not find IT Glue organization id for {organization}")
		
		else:

			for each in contacts:
				email = each['email']

				#Remove extra characters from phone numbers
				phone = re.sub("[^0-9]","",each['phone'])
				mobile = re.sub("[^0-9]","",each['mobile'])

				if each['standing']=='active':
					ctype = 138082 #replace with appropriate itglue contact-type-id
				elif each['standing']=='inactive':
					ctype = 138081 #replace with appropriate itglue contact-type-id

			#Create json data to send to IT Glue

				data = {
					"data" : {
						"type" : "contacts",
						"attributes" :{
							"first_name" : f"{each['firstname']}",
							"last_name" : f"{each['surname']}",
							"title" : f"{each['position']}",
							"location-name" : f"{each['physical_address']['title']}",
							"contact-type-id" : ctype,
							"contact-emails" : [
								{
									"value" :f"{email}",
									"primary" : True,
									"label-name" : "Email"
								}
							],
							"contact-phones" : [
								{
									"label-name" : "Work",
									"value" : phone
								},
								{
									"label-name" : "Mobile",
									"value" : mobile
								}
							]

						}
					}
				}
				print(data['data']['attributes']['first_name'], data['data']['attributes']['last_name'])

				# If there is no phone or mobile info remove from list
				
				if not each['phone'] and not each['mobile']:
					data['data']['attributes']['contact-phones'].pop(0)
					data['data']['attributes']['contact-phones'].pop(0)
				elif not each['phone']:
					data['data']['attributes']['contact-phones'].pop(0)
				elif not each['mobile']:
					data['data']['attributes']['contact-phones'].pop(1)
				
			

			# If an email exists in contact, search for it in IT Glue and retrieve contact id #
				if email:
					search = get_itg(f"https://api.itglue.com/contacts?filter[primary_email]={email}",itg_headers)['data']
					
					
			# If email found in IT Glue, update Contact using PATCH /organizations/:organization_id/relationships/contacts/:id
					if search:
						contact_id = search[0]["id"]
						print(f'id: {contact_id}')
						r = patch(f"https://api.itglue.com/organizations/{org_id}/relationships/contacts/{contact_id}",itg_headers,data)
						if r: 
							print(r.text)

			# If email not found in IT Glue, create Contact using POST /organizations/:organization_id/relationships/contacts

					else: 
						print("contact not found- creating contact")
						r = post(f"https://api.itglue.com/organizations/{org_id}/relationships/contacts",itg_headers,data)
						if r: 
							print(r.text)



