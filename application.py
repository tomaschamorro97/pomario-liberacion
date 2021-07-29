from __future__ import print_function
from flask import Flask, render_template, render_template_string, Response, redirect, url_for, jsonify, after_this_request
from flask import request
import time
import os.path
import datetime as DT
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import urllib.request
from pyzbar import pyzbar
import cv2
import datetime

hojaPantalla = "1LoDbgrhnigeRQCWaQ6eImgzkihAqynRPB1k3UbRK6y0"
hojaLiberacion = "1KODazTs91ogpl5oIa9oGwLdZ0QS4FHRJj8RdPAKII6s"
today = datetime.datetime.now()
noWeek = datetime.date(int(today.strftime("%Y")), int(today.strftime("%m")), int(today.strftime("%d"))).strftime("%V")
day_of_week = today.strftime("%w")
day_of_year = (today - datetime.datetime(today.year, 1, 1)).days + 1
if day_of_year < 10:
    day_of_year = "00" + str(day_of_year)
elif day_of_year < 100:
    day_of_year = "0" + str(day_of_year)
else:
    day_of_year = str(day_of_year)

app = Flask(__name__)
g = {"aLiberar": "", "infoEscaneo": "", "noCelda" : 0, "qtyFacturada" : "", "codProducto":"", "nomProducto" : "",
 "strLiberacion": " ", "pesoProducto": 0, "tipoEmpaque": "", "pesoEmpaque" : "", "temProducto" : 0, "contraMuestra": False, "udsInspeccion": 0,
 "aRechazar" : "0","PE_pesoNeto" : "C", "PE_etiquetado" : "C", "PE_empaque" : "C", "PE_especificacion" : "C", "PE_inocuidad" : "C", 
 "observacionRechazo" : ""}

@app.route("/<int:celsius>")
def fahrenheit_from(celsius):
    """Convert Celsius to Fahrenheit degrees."""
    try:
        fahrenheit = float(celsius) * 9 / 5 + 32
        fahrenheit = round(fahrenheit, 3)  # Round to three decimal places
        return str(fahrenheit)
    except ValueError:
        return "invalid input"


@app.route("/")
def index():
    RangoDatos = 'Inventario_Transito!A2:I'
    bdProductos, contador = extraerDatos(RangoDatos, hojaPantalla)
    RangoDatosLib = 'Original!A8:A26'
    #appendLiberacion(RangoDatosLib)
    if g["infoEscaneo"] != "":
        skuProducto = g["infoEscaneo"]
    else:
        skuProducto = request.args.get("skuProducto2", "").upper()

    codProducto = ""
    if g["strLiberacion"] != "":
        strLiberacion = g["strLiberacion"]
        g["strLiberacion"] = ""
    else:
        strLiberacion = "No se ha ingresado ningún producto"
    nomProducto = ""
    noCelda = ""
    qtyFacturada = 0
    if skuProducto != "":
        for pdct in bdProductos:
            codProducto = pdct[1]
            if codProducto == skuProducto:
                nomProducto = pdct[2]
                noCelda = pdct[0]
                qtyFacturada = pdct[3]
                pesoProducto = pdct[8]
                tipoEmpaque = pdct[7]
                pesoEmpaque = pdct[9]
                break
            codProducto = "not found"
    
    if skuProducto != "" and codProducto != "not found":
        g["noCelda"] = noCelda
        g["qtyFacturada"] = qtyFacturada
        g["nomProducto"] = nomProducto
        g["codProducto"] = codProducto
        g["pesoProducto"] = pesoProducto
        g["tipoEmpaque"] = tipoEmpaque
        g["pesoEmpaque"] = pesoEmpaque
        
        return redirect(url_for('liberar_producto'))
        #strLiberacion = "Producto encontrado: " + nomProducto #+ ". Número de celda: " + noCelda + ". Cantidad facturada: " + qtyFacturada
    elif codProducto == "not found":
        g["infoEscaneo"] = ""

    if skuProducto != "" and codProducto == "not found":
        strLiberacion = "No se encontró el producto con SKU " + skuProducto + " en el Drive de Google. Favor verifique y vuelva a correr."
        camera.codigo = False
        camera.is_decoded = False
        return render_template('noEncontrado.html',strLiberacion=strLiberacion)
    
    return render_template('index.html',strLiberacion=strLiberacion)

@app.route("/notFound")
def notfound():
    #camera = Camera()
    g["strLiberacion"] = ""
    g["infoEscaneo"] = ""
    return redirect(url_for('index'))


@app.route("/liberar_producto")
def liberar_producto():
    infoEscaneo = g["infoEscaneo"]
    noCelda = g["noCelda"]
    qtyFacturada = g["qtyFacturada"]
    codProducto = g["codProducto"]
    nomProducto = g["nomProducto"]
    qtyFacturada = g["qtyFacturada"]
    pesoProducto = request.args.get("pesoProducto", "")
    g["aLiberar"] = request.args.get("aLiberar", "")
    g["temProducto"] = request.args.get("temProducto", "")
    g["contraMuestra"] = request.args.get("yes_no", "")
    g["udsInspeccion"] = request.args.get("udsInspeccion", "")
    if request.args.get("pesoBruto", "") != "":
        g["pesoEmpaque"] = str(int(request.args.get("pesoBruto", "")) - int(pesoProducto))
        g["pesoProducto"] = pesoProducto
    strLiberacion = ""
    aprueba = """Francisco-Acosta"""
    g["strLiberacion"] = ""
    if g["aLiberar"] and noCelda != 0:
        RangoDatos = 'Inventario_Transito!C' + str(noCelda)
        appendLiberacion()
        qtyLiberados = ingresarDatos(int(g["aLiberar"]) + int(qtyFacturada),RangoDatos,hojaPantalla)
        if qtyLiberados != 0:
            g["strLiberacion"] = codProducto + " - " + nomProducto +" - Se liberaron " + str(g["aLiberar"]) + " unidades satisfactoriamente"
            g["infoEscaneo"] = ""
            print(g)
            return redirect(url_for('index'))

    return (
            """<h2> Producto a liberar: """ + codProducto + """ - """ + nomProducto + """ </h2> 
            <form action="/rechazar_producto">
                    <input type="submit" value="Rechazar producto">
            </form>
            <p><form action="" method="get">
                    <p>Indique cantidad a liberar: <input type="text" name="aLiberar"</p>
                    <p>Indique temperatura del producto: <input type="text" name="temProducto"</p>
                    <p>Unidades inspeccionadas: <input type="text" name="udsInspeccion" </input> </p>
                    <p>Tipo de empaque: <input type="text" name="tipoEmpaque" value = """ + g["tipoEmpaque"] + """></input></p>
                    <p>Peso neto: <input type="text" name="pesoProducto" value = """ + str(g["pesoProducto"]) + """></input></p>
                    <p>Peso bruto: <input type="text" name="pesoBruto" value = """ + str(int(g["pesoProducto"])+int(g["pesoEmpaque"])) + """></input></p>
                    <p>Aprueba: <input type="text" name="aprueba" value = """ + aprueba + """></input></p>
                    <div id="wrapper">
                    <label for="yes_no_radio">¿Es contra muestra?</label>
                    <p>
                    <input type="radio" name="yes_no" value = "Si" >Si</input>
                    <input type="radio" name="yes_no" value = "No" checked>No</input>
                    </p>
                    </div>
                    <input type="submit" value="Liberar producto"</input> </p>
                </form>
                <form action="/redirectqr">
                    <input type="submit" value="Escanear de nuevo">
                </form>
                <form action="/redirecthome">
                    <input type="submit" value="Volver al inicio">
                </form></p>"""

    )

@app.route("/rechazar_producto")
def rechazar_producto():
    noCelda = g["noCelda"]
    qtyFacturada = g["qtyFacturada"]
    codProducto = g["codProducto"]
    nomProducto = g["nomProducto"]
    pesoProducto = request.args.get("pesoProducto", "")
    g["aRechazar"] = request.args.get("aRechazar", "")
    g["temProducto"] = request.args.get("temProducto", "")
    g["contraMuestra"] = request.args.get("yes_no", "")
    g["udsInspeccion"] = request.args.get("udsInspeccion", "")
    g["PE_pesoNeto"] = request.args.get("PE_pesoNeto", "")
    g["PE_etiquetado"] = request.args.get("PE_etiquetado", "")
    g["PE_empaque"] = request.args.get("PE_empaque", "")
    g["PE_especificacion"] = request.args.get("PE_especificacion", "")
    g["PE_inocuidad"] = request.args.get("PE_inocuidad", "")
    g["observacionRechazo"] = request.args.get("observacionRechazo", "")
    if request.args.get("pesoBruto", "") != "":
        g["pesoEmpaque"] = str(int(request.args.get("pesoBruto", "")) - int(pesoProducto))
        g["pesoProducto"] = pesoProducto
    if g["aRechazar"] and noCelda != 0:
        checkNC = False
        for key in g:
            if g[key] == "NC":
                checkNC = True
                break
        if checkNC:
            appendLiberacion()
            g["strLiberacion"] = codProducto + " - " + nomProducto +" - se agregó satisfactoriamente el rechazo de " + str(g["aLiberar"]) + " unidades a la hoja de liberación"
            g["infoEscaneo"] = ""
            return redirect(url_for('index'))
        else:
            g["strLiberacion"] = "Favor indique el motivo de rechazo. Almenos un parametro de evaluación debe ser 'No Conforme' (NC)"
    rechaza = """Francisco-Acosta"""
    return (
            """
            <h2>Producto a rechazar: """ + codProducto + """ - """ + nomProducto + """</h2>
            <h3> <font color = "red"> """ + g["strLiberacion"] + """ </font></h3>
            <form action="" method="get">
                    <p>Indique cantidad a rechazar: <input type="text" name="aRechazar"</p>
                    <p>Indique temperatura del producto: <input type="text" name="temProducto"</p>
                    <p>Unidades inspeccionadas: <input type="text" name="udsInspeccion" </input> </p>
                    <p>Tipo de empaque: <input type="text" name="tipoEmpaque" value = """ + g["tipoEmpaque"] + """></input></p>
                    <p>Peso neto: <input type="text" name="pesoProducto" value = """ + str(g["pesoProducto"]) + """></input></p>
                    <p>Peso bruto: <input type="text" name="pesoBruto" value = """ + str(int(g["pesoProducto"])+int(g["pesoEmpaque"])) + """></input></p>
                    <p>Rechaza: <input type="text" name="rechaza" value = """ + rechaza + """></input></p>
                    <div id="wrapper">
                    <h2>Razón del rechazo </h2>
                    <p><label for="yes_no_radio">Peso neto</label>
                    <input type="radio" name="PE_pesoNeto" value = "C" checked>C</input>
                    <input type="radio" name="PE_pesoNeto" value = "NC" >NC</input></p>
                    <p><label for="yes_no_radio">Etiquetado/Rotulado</label>
                    <input type="radio" name="PE_etiquetado" value = "C" checked>C</input>
                    <input type="radio" name="PE_etiquetado" value = "NC" >NC</input></p>
                    <p><label for="yes_no_radio">Calidad del empaque</label>
                    <input type="radio" name="PE_empaque" value = "C" checked>C</input>
                    <input type="radio" name="PE_empaque" value = "NC" >NC</input></p>
                    <p><label for="yes_no_radio">Especificación</label>
                    <input type="radio" name="PE_especificacion" value = "C" checked>C</input>
                    <input type="radio" name="PE_especificacion" value = "NC" >NC</input></p>
                    <p><label for="yes_no_radio">Inocuidad</label>
                    <input type="radio" name="PE_inocuidad" value = "C" checked>C</input>
                    <input type="radio" name="PE_inocuidad" value = "NC" >NC</input></p>
                    </div>
                    <label>Descripción del rechazo:</label>
                    <p><textarea name="observacionRechazo" rows="4" cols="50">
                    </textarea></p>
                    <p><input type="submit" value="Rechazar producto"</input> </p>
                </form>
                <form action="/redirectqr">
                    <input type="submit" value="Escanear de nuevo">
                </form>
                <form action="/redirecthome">
                    <input type="submit" value="Volver al inicio">
                </form>"""
    )


@app.route("/redirecthome")
def redirecthome():
    g["aLiberar"] =  ""
    g["infoEscaneo"] =  ""
    g["noCelda"] =  0
    g["qtyFacturada"]=  ""
    g["codProducto"] = ""
    g["nomProducto"] = ""
    g["strLiberacion"] = " "
    g["pesoProducto"] = 0
    g["tipoEmpaque"] = ""
    g["pesoEmpaque"] = ""
    g["temProducto"] = 0
    g["contraMuestra"] = "No"
    g["udsInspeccion"] = 0
    g["aRechazar"] = 0
    g["PE_pesoNeto"] = "C"
    g["PE_etiquetado"] = "C"
    g["PE_empaque"] = "C"
    g["PE_especificacion"] = "C"
    g["PE_inocuidad"] = "C"
    g["observacionRechazo"] = ""
    return redirect(url_for('index'))

    

@app.route("/qrdetected")

def qrdetected():
    camera = get_camera()
    g["infoEscaneo"] = camera.barcode_info
    return redirect(url_for('index'))





class Camera():
    
    def __init__(self):
        self.video = cv2.VideoCapture(1)
        self.start_time = time.time() 
        self.stop_time  = self.start_time + 20
        self.is_decoded = False  # keep it to send it with AJAX
        self.codigo = False
        self.barcode_info = ""
        self.stat = True
        
    def __del__(self):
        self.video.release()
        
    def get_feed(self):
        stat, frame = self.video.read()
        self.stat = stat
        ret, jpeg = cv2.imencode('.jpg', frame)
        
        self.is_decoded = (time.time() >= self.stop_time) or (self.codigo == True) # stop stream after 5 seconds
        
        return jpeg.tobytes(), self.is_decoded, stat, frame
    

camera = Camera()

# send the same camera to two functions
def get_camera():
    return camera
    
def gen(camera):
    # start timer only when start streaming
    camera.start_time = time.time()
    camera.stop_time = camera.start_time + 20
    barcode_info = ""
    while True:
        frame, is_decoded, stat, frame2 = camera.get_feed() 
        
        if is_decoded:
            print('stop stream')
            break
        barcode_info = ""
        barcodes = pyzbar.decode(frame2)
        for barcode in barcodes:
            x, y , w, h = barcode.rect
            #1
            barcode_info = barcode.data.decode('utf-8')
            cv2.rectangle(frame2, (x, y),(x+w, y+h), (0, 255, 0), 2)
            
            #2
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame2, barcode_info, (x + 6, y - 6), font, 2.0, (255, 255, 255), 1)
            if barcode_info != "":
                camera.barcode_info = barcode_info
                camera.codigo = True
        yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        

@app.route('/video_feed/')
def video_feed():
    camera = get_camera()
    camera.is_decoded = False
    return Response(gen(camera), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/redirectqr/')
def redirectqr():
    camera = get_camera()
    camera.is_decoded = False
    camera.codigo = False
    camera.barcode_info = ""
    return redirect(url_for('qrcheck'))

@app.route('/is_decoded/')
def is_decoded():
    camera = get_camera()
    return jsonify({'is_decoded': camera.is_decoded, 'barcode_info': camera.barcode_info})
    
@app.route('/notDetected')
def notDetected():
    g["infoEscaneo"] = ""
    g["strLiberacion"] = "No se detectó ningun producto durante el escaneo. Favor ingresar el código manualmente o vuelva a intentar"
    camera = get_camera() 
    camera.is_decoded = False
    camera.barcode_info = ""
    return redirect(url_for('index'))


@app.route('/qrcheck')
def qrcheck():
    camera.codigo = False
    return render_template('qrcheck.html')

def ingresarDatos(valEnviar,RangoDatos,libro):
    values = [[valEnviar]]
    body = {
    'values': values
    }
    try:
        hojaGoogle,service = conGoogle(libro)
        result = service.spreadsheets().values().update(
        spreadsheetId=hojaGoogle, range=RangoDatos,
        valueInputOption="RAW", body=body).execute()
        if str(valEnviar) == "":
            print('No se ingresó nada')
            return 0
        else:
            print('Se actualizó el inventario a:', valEnviar)
            return valEnviar

        #print('{0} cells updated.'.format(result.get('updatedCells')))
    except:
        print('No hay conexión a Internet')
        return 0

def appendLiberacion():
    hojaGoogle,service = conGoogle(hojaLiberacion)
    sheet = service.spreadsheets()
    ultHoja = sheet.values().get(spreadsheetId=hojaLiberacion,
                                range='Original!X4:Y4').execute()
    noHoja = ultHoja.get('values', [])[0][0].split()[-1]
    indexHoja = int(noHoja) + 1
    nombreHoja = "Hoja" + str(int(noHoja)) + "!A8:A26"
    ultFila = len(sheet.values().get(spreadsheetId=hojaLiberacion,
                                range=nombreHoja).execute().get('values', []))
    RangoAppend = "Hoja" + str(int(noHoja)) + "!A8:Y8"
    if ultFila == 19:
        duplicarHoja()
        appendLiberacion()
    else:
        lst = genList()
        data = []
        for val in lst:
            data.append(val)
        ValueRange = {"range" : RangoAppend, "values" : [data]}
        sheet.values().append(spreadsheetId=hojaLiberacion,body=ValueRange,valueInputOption= "RAW", range=RangoAppend).execute()
        if g["observacionRechazo"].split() != "":
            rangActualizar = "Hoja" + str(int(noHoja)) + "!B27:Y28"
            result = sheet.values().get(spreadsheetId=hojaLiberacion,
                                range= rangActualizar).execute().get('values', [])
            try:
                concat = result[0][0] + ", " + g["observacionRechazo"]
            except:
                concat = g["observacionRechazo"]
            body = {'values': [[concat]]}
            service.spreadsheets().values().update(
            spreadsheetId=hojaLiberacion, range=rangActualizar,
            valueInputOption="RAW", body=body).execute()



        
    


def duplicarHoja():
    idHoja = 166124872
    hojaGoogle,service = conGoogle(hojaLiberacion)
    RangoDatos = 'Original!X4:Y4'
    sheet = service.spreadsheets()
    result1 = sheet.values().get(spreadsheetId=hojaLiberacion,
                                range='Original!X4:Y4').execute()
    print(result1.get('values', [])[0][0].split())
    noHoja = result1.get('values', [])[0][0].split()[-1]
    indexHoja = int(noHoja) + 1
    nombreHoja = "Hoja" + str(int(noHoja)+1)
    jsonDuplicar = {"sourceSheetId": idHoja,
        "insertSheetIndex": indexHoja,
        "newSheetName": nombreHoja}
    requestDuplicate = {"duplicateSheet" : jsonDuplicar}
    bodyRequest = {"requests": [requestDuplicate]}
    sheet.batchUpdate(spreadsheetId=hojaLiberacion,
                                body = bodyRequest).execute()
    valEnviar = "PAGINA: 0 de " + str(int(noHoja)+1)
    values = [[valEnviar]]
    body = {
    'values': values
    }
    service.spreadsheets().values().update(
    spreadsheetId=hojaGoogle, range=RangoDatos,
    valueInputOption="RAW", body=body).execute()
    data = []
    rangoIt = range(1,(int(noHoja) + 2))
    for i in rangoIt:
        rango = "Hoja" + str(i) + "!X4:Y4"
        values1 = [["PAGINA: " + str(i) + " de " + str(int(noHoja)+1)]]
        ValueRange = {"range" : rango, "values" : values1}
        data.append(ValueRange)
    rango2 = nombreHoja + "!B4:C4"
    value2 = DT.date.today().strftime("%d-%m-%Y")
    data.append({"range" : rango2, "values" : [[value2]]})
    rango3 = nombreHoja + "!E4:J4"
    value3 = "L"+str(noWeek)+"0"+day_of_week+str(day_of_year)
    data.append({"range" : rango3, "values" : [[value3]]})
    rango4 = nombreHoja + "!Q4:W4"
    value4 = (DT.date.today() + DT.timedelta(days=7)).strftime("%d-%m-%Y")
    data.append({"range" : rango4, "values" : [[value4]]})
    if int(noHoja)+1 == 2:
        data.append({"range" : "Hoja1!B4:C4", "values" : [[value2]]})
        data.append({"range" : "Hoja1!E4:J4", "values" : [[value3]]})
        data.append({"range" : "Hoja1!Q4:W4", "values" : [[value4]]})

    bodyUpdate = {"valueInputOption" : "RAW", "data" : [data]}
    sheet.values().batchUpdate(spreadsheetId=hojaLiberacion,body=bodyUpdate).execute()
    

def extraerDatos(RangoDatos, Spreadsheet):
    hojaGoogle,service = conGoogle(Spreadsheet)
    # Call the Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=Spreadsheet,
                                range=RangoDatos).execute()
    values = result.get('values', [])
    #print(result)
    productos = []
    if not values:
        print('No data found.')
    else:
        #print('Name, Major:')
        count = 2
        for row in values:
            # Print columns A and E, which correspond to indices 0 and 4.
            productos.append([count,row[0],row[1],row[2],row[3],row[4],row[5],row[6],row[7],row[8]])
            count += 1
        #print(productos)
    return productos,count

def conGoogle(SAMPLE_SPREADSHEET_ID):
    # If modifying these scopes, delete the file token.json.
    #SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    # The ID and range of a sample spreadsheet.
    
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the firFst
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('sheets', 'v4', credentials=creds)
    return SAMPLE_SPREADSHEET_ID,service

def genList():
    lstLib = [""] * 25
    lstLib[0] = g["nomProducto"]
    lstLib[1] = g["tipoEmpaque"]
    lstLib[2] = g["pesoProducto"]
    lstLib[3] = str(int(g["pesoProducto"]) + int(g["pesoEmpaque"]))
    if g["PE_pesoNeto"] == "C":
        lstLib[4] = "X"
    else:
        lstLib[5] = "X"
    if g["PE_etiquetado"] == "C":
        lstLib[6] = "X"
    else:
        lstLib[7] = "X"
    if g["PE_empaque"] == "C":
        lstLib[8] = "X"
    else:
        lstLib[9] = "X"
    if g["PE_especificacion"] == "C":
        lstLib[10] = "X"
    else:
        lstLib[11] = "X"
    if g["PE_inocuidad"] == "C":
        lstLib[12] = "X"
    else:
        lstLib[13] = "X"
    lstLib[14] = g["temProducto"]
    if g["aLiberar"] == "":
        lstLib[15] = g["aRechazar"]
    else:
        lstLib[15] = g["aLiberar"]
    lstLib[17] = g["udsInspeccion"]
    if g["contraMuestra"] == "No" or int(g["aRechazar"]) > 0:
        lstLib[20] = "X"
    else:
        lstLib[19] = "X"
    lstLib[21] = "X"
    if int(g["aRechazar"]) > 0:
        lstLib[24] = "Francisco-Acosta"
    else:
        lstLib[23] = "Francisco-Acosta"
    return lstLib



if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)


