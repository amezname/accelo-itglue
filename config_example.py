import base64

# Accelo Deployment
deployment = 'AcceloDeployment'

#Accelo client credentials converted to base64
client_id = 'Client ID'
client_secret = 'Client Secret'
combine = f'{client_id}:{client_secret}'
combine_enc = combine.encode('ascii')
combine_b64 = base64.b64encode(combine_enc)
acc_credentials = combine_b64.decode('ascii')

#IT Glue API Key
api_key = 'API Key'

#Logger Filepath
filepath = 'File path'