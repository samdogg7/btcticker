
#!/usr/bin/python3
from PIL import Image, ImageOps
from PIL import ImageFont
from PIL import ImageDraw
import currency
import os
import sys
import logging
import RPi.GPIO as GPIO
from waveshare_epd import epd2in7
import time
import random
import requests
import urllib, json
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import yaml
import socket
picdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'images')
fontdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fonts')
configfile = os.path.join(os.path.dirname(os.path.realpath(__file__)),'config.yaml')
fonthiddenprice = ImageFont.truetype(os.path.join(fontdir,'googlefonts/Roboto-Medium.ttf'), 30)
font = ImageFont.truetype(os.path.join(fontdir,'googlefonts/Roboto-Medium.ttf'), 40)
fontHorizontal = ImageFont.truetype(os.path.join(fontdir,'googlefonts/Roboto-Medium.ttf'), 50)
font_date = ImageFont.truetype(os.path.join(fontdir,'PixelSplitter-Bold.ttf'),11)
font_quote = ImageFont.truetype(os.path.join(fontdir,'googlefonts/Roboto-Medium.ttf'), 18)

def internet(host="8.8.8.8", port=53, timeout=3):
    """
    Host: 8.8.8.8 (google-public-dns-a.google.com)
    OpenPort: 53/tcp
    Service: domain (DNS/TCP)
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error as ex:
        logging.info("No internet")
        return False


def getData(whichcoin,fiat,timeframe):
    """
    The function to update the ePaper display. There are two versions of the layout. One for portrait aspect ratio, one for landscape.
    """
    # Get the week window in msec from epoch. This is used in the api calls
    logging.info("Getting Data")
    now_msec_from_epoch = int(round(time.time() * 1000))
    endtime = now_msec_from_epoch
    starttime = endtime - 1000*60*60*24*int(timeframe)
    starttimeseconds = round(starttime/1000)  #CoinGecko Uses seconds
    endtimeseconds = round(endtime/1000)      #CoinGecko Uses seconds

    # Get the price
    try:
        geckourl = "https://api.coingecko.com/api/v3/coins/markets?vs_currency="+fiat+"&ids="+whichcoin
        logging.info(geckourl)
        rawlivecoin = requests.get(geckourl).json()
        liveprice= rawlivecoin[0]
        pricenow= float(liveprice['current_price'])
        logging.info("Got Live Data From CoinGecko")
        geckourlhistorical = "https://api.coingecko.com/api/v3/coins/"+whichcoin+"/market_chart/range?vs_currency="+fiat+"&from="+str(starttimeseconds)+"&to="+str(endtimeseconds)
        logging.info(geckourlhistorical)
        rawtimeseries = requests.get(geckourlhistorical).json()
        logging.info("Got Historical Data For Last " + str(timeframe) + " days from CoinGecko")
        timeseriesarray = rawtimeseries['prices']
        timeseriesstack = []
        length=len (timeseriesarray)
        i=0
        while i < length:
            timeseriesstack.append(float (timeseriesarray[i][1]))
            i+=1
    except:
        logging.info("Coingecko is unreachable - Exit the script")
        sys.exit()

    # Add live price to timeseriesstack
    timeseriesstack.append(pricenow)
    return timeseriesstack

def makeSpark(pricestack):

    # Subtract the mean from the sparkline to make the mean appear on the plot (it's really the x axis)
    x = pricestack-np.mean(pricestack)

    fig, ax = plt.subplots(1,1,figsize=(10,3))
    plt.plot(x, color='k', linewidth=6)
    plt.plot(len(x)-1, x[-1], color='r', marker='o')

    # Remove the Y axis
    for k,v in ax.spines.items():
        v.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axhline(c='k', linewidth=4, linestyle=(0, (5, 2, 1, 2)))

    # Save the resulting bmp file to the images directory
    plt.savefig(os.path.join(picdir,'spark.png'), dpi=17)
    imgspk = Image.open(os.path.join(picdir,'spark.png'))
    file_out = os.path.join(picdir,'spark.bmp')
    imgspk.save(file_out)


def updateDisplay(config,pricestack,whichcoin,fiat,timeframe,random_quotes):

    symbolstring=currency.symbol(fiat.upper())
    if fiat=="jpy":
        symbolstring="¥"

    pricenow = pricestack[-1]
    currencythumbnail= 'currency/'+whichcoin+'.bmp'
    tokenimage = Image.open(os.path.join(picdir,currencythumbnail))
    sparkbitmap = Image.open(os.path.join(picdir,'spark.bmp'))
    timestring = time.strftime("%a %b %d - %-I:%M %p")


    pricechange = str("%+d" % round((pricestack[-1]-pricestack[0])/pricestack[-1]*100,2))+"%"
    if pricenow > 1000:
        pricenowstring =format(int(pricenow),",")
    else:
        pricenowstring =str(float('%.5g' % pricenow))

    timeframe_text = " days "
    if int(timeframe) <= 1:
        timeframe_text = " day "

    if config['display']['orientation'] == 0 or config['display']['orientation'] == 180 :
        epd = epd2in7.EPD()
        epd.Init_4Gray()
        image = Image.new('L', (epd.width, epd.height), 255)    # 255: clear the image with white
        draw = ImageDraw.Draw(image)
        draw.text((110,80),str(timeframe) + timeframe_text,font =font_date,fill = 0)
        draw.text((110,95),pricechange,font =font_date,fill = 0)
        # Print price to 5 significant figures
        draw.text((5,200),symbolstring+pricenowstring,font =font,fill = 0)
        draw.text((0,10),str(time.strftime("%c")),font =font_date,fill = 0)
        image.paste(tokenimage, (10,25))
        image.paste(sparkbitmap,(10,125))
        if config['display']['orientation'] == 180 :
            image=image.rotate(180, expand=True)


    if config['display']['orientation'] == 90 or config['display']['orientation'] == 270 :
        epd = epd2in7.EPD()
        epd.Init_4Gray()
        image = Image.new('L', (epd.height, epd.width), 255)    # 255: clear the image with white
        random_quote = random.choice(random_quotes)
        draw = ImageDraw.Draw(image)
        draw.text((100,80), str(timeframe) + timeframe_text + pricechange,font =font_date,fill = 0)
        # Print price to 5 significant figures
        draw.text((5,95),"$"+pricenowstring,font =fontHorizontal,fill = 0)
        image.paste(sparkbitmap,(80,30))
        image.paste(tokenimage, (0,0))
        draw.text((100,5),timestring,font =font_date,fill = 0)
        draw.text((5,150),random_quote,font =font_quote,fill = 0)
        if config['display']['orientation'] == 270 :
            image=image.rotate(180, expand=True)
#       This is a hack to deal with the mirroring that goes on in 4Gray Horizontal
        image = ImageOps.mirror(image)

#   If the display is inverted, invert the image usinng ImageOps
    if config['display']['inverted'] == True:
        image = ImageOps.invert(image)
#   Send the image to the screen
    epd.display_4Gray(epd.getbuffer_4Gray(image))
    epd.sleep()

def main():

    logging.basicConfig(level=logging.DEBUG)

    try:
        logging.info("epd2in7 BTC Frame")
#       Get the configuration from config.yaml

        with open(configfile) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        logging.info(config)
        GPIO.setmode(GPIO.BCM)
        config['display']['orientation']=int(config['display']['orientation'])

        currencystring = config['ticker']['currency']
        crypto_list = currencystring.split(",")
        crypto_list = [x.strip(' ') for x in crypto_list]
        logging.info(crypto_list)

        fiatstring=config['ticker']['fiatcurrency']
        fiat_list = fiatstring.split(",")
        fiat_list = [x.strip(' ') for x in fiat_list]
        logging.info(fiat_list)
        
        coinnumber = 0
        CURRENCY=crypto_list[coinnumber]
        FIAT=fiat_list[coinnumber]
        
        timeframestring=config['ticker']['timeframes']
        timeframes_list = timeframestring.split(",")
        timeframes_list = [x.strip(' ') for x in timeframes_list]
        TIMEFRAME=timeframes_list[0]
        
        RANDOMQUOTES = config['ticker']['randomquotes']
        
        logging.info(CURRENCY)
        logging.info(FIAT)
        key1 = 5
        key2 = 6
        key3 = 13
        key4 = 19

        GPIO.setup(key1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(key2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(key3, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(key4, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#       Note that there has been no data pull yet
        datapulled=False
#       Time of start
        lastcoinfetch = time.time()

        while True:
            key1state = GPIO.input(key1)
            key2state = GPIO.input(key2)
            key3state = GPIO.input(key3)
            key4state = GPIO.input(key4)

            if internet():
                if key1state == False:
                    logging.info('Cycle currencies')
                    # Rotate the array of currencies from config.... [a b c] becomes [b c a]
                    crypto_list = crypto_list[1:]+crypto_list[:1]
                    CURRENCY=crypto_list[0]
                    # Write back to config file
                    config['ticker']['currency']=",".join(crypto_list)
                    with open(configfile, 'w') as f:
                       data = yaml.dump(config, f)
                    logging.info(CURRENCY)
                    # get data
                    pricestack=getData(CURRENCY,FIAT,TIMEFRAME)
                    # save time of last data update
                    lastcoinfetch = time.time()
                    # generate sparkline
                    makeSpark(pricestack)
                    # update display
                    updateDisplay(config, pricestack, CURRENCY,FIAT,TIMEFRAME,RANDOMQUOTES)
#                   time.sleep(0.2)
                if key2state == False:
                    logging.info('Rotate - 90')
                    config['display']['orientation'] = (config['display']['orientation']+90) % 360
                    # update display
                    updateDisplay(config, pricestack, CURRENCY,FIAT,TIMEFRAME,RANDOMQUOTES)
                    # Write back to config file
                    with open(configfile, 'w') as f:
                       data = yaml.dump(config, f)
#                   time.sleep(0.2)
                if key3state == False:
                    logging.info('Invert Display')
                    if config['display']['inverted'] == True:
                       config['display']['inverted'] = False
                    else:
                       config['display']['inverted'] = True
                    # update display
                    updateDisplay(config, pricestack, CURRENCY,FIAT,TIMEFRAME,RANDOMQUOTES)
                    with open(configfile, 'w') as f:
                       data = yaml.dump(config, f)
                    lastcoinfetch=time.time()
#                   time.sleep(0.2)
                if key4state == False:
                    logging.info('Cycle time frame')
                    # Rotate the array of time frame.... [1 7 30] becomes [7 30 1]
                    timeframes_list = timeframes_list[1:]+timeframes_list[:1]
                    TIMEFRAME=timeframes_list[0]
                    config['ticker']['timeframes']=",".join(timeframes_list)
                    with open(configfile, 'w') as f:
                       data = yaml.dump(config, f)
                    # get data
                    pricestack=getData(CURRENCY,FIAT,TIMEFRAME)
                    # save time of last data update
                    lastcoinfetch = time.time()
                    # generate sparkline
                    makeSpark(pricestack)
                    # update display
                    updateDisplay(config, pricestack, CURRENCY,FIAT,TIMEFRAME,RANDOMQUOTES)
#                   time.sleep(0.2)
                if (time.time() - lastcoinfetch > float(config['ticker']['updatefrequency'])) or (datapulled==False):
                    # get data
                    pricestack=getData(CURRENCY,FIAT,TIMEFRAME)
                    # save time of last data update
                    lastcoinfetch = time.time()
                    # generate sparkline
                    makeSpark(pricestack)
                    # update display
                    updateDisplay(config, pricestack, CURRENCY,FIAT,TIMEFRAME,RANDOMQUOTES)
                    # Note that we've visited the internet
                    datapulled = True
                    lastcoinfetch=time.time()


    except IOError as e:
        logging.info(e)

    except KeyboardInterrupt:
        logging.info("ctrl + c:")
        epd2in7.epdconfig.module_exit()
        exit()

if __name__ == '__main__':
    main()
