# meghavi
meghavi_script.py : Main python script which detects human presence using their face and triggers the screensaver actions (stop or start)

meghavi_functions.py : This file servers all functions required for main script like to downloading videos from server,checking for new videos

download_zip_popup.py : shows videos downloading from server as progress bar on main screen

screensaver.py & webview_scrnsaver.py : main scripts which displays videos as screensaver using python webview library

caliberation.py : script to manually note distinct values to train the face detection algorithm to measure distance 
                    steps:
                    1. Take a measurement tape and place your face at specific distance
                    2.Enter "c" and write the distance that you placed your face to program
                    3. do it 10 - 15 times placing at different distances for better accurcay
                    4. press 'q' after completing and open caliberation.json file to check the distances you set
                    5. Run calibertaion_fit.py and note down a and b values

caliberation_fit.py :  take 'a' and 'b' values and use them in "meghvai_script.py"

Note: This caliberation should be donw if you change the camera you are using is of different specs as previous one.

app.py: (backend code ) should be run to server local videos to html
