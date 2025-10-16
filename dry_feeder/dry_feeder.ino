
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include "password.hpp"

const int LED_PIN = LED_BUILTIN;
const int MEAL_PIN = 9; // green line -> GPIO9 / D10
unsigned long meal_count = 0;
const int SNACK_PIN = 8; // white line -> GPIO8 / D9
unsigned long snack_count = 0;

// example:
// 4.00s: press the button
// 6.00s: the machine starts to dispense the meal (the be safe, wait for 4s)
// 12.00s: the machine is ready for the next command

unsigned long previous_feed = 0;
const unsigned long feed_interval = 8000;  // 8 seconds
const unsigned long press_duration = 4000; // 4 seconds

WebServer server(80);

void root()
{
  digitalWrite(LED_PIN, HIGH);
  String message = "";
  message += "<h3>meal count: " + String(meal_count) + "</h3>";
  message += "<h3>snack count: " + String(snack_count) + "</h3>";
  message += "Click <a href=\"/on\">/on</a> to turn the LED on.<br>";
  message += "Click <a href=\"/off\">/off</a> to turn the LED off.<br>";
  message += "Click <a href=\"/meal\">/meal</a> to feed meal.<br>";
  message += "Click <a href=\"/snack\">/snack</a> to feed snack.<br>";
  server.send(200, "text/html", message);
  digitalWrite(LED_PIN, LOW);
}

void on()
{
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  Serial.println("request: /on");
  server.send(200, "text/html", "LED on");
}

void off()
{
  digitalWrite(LED_PIN, HIGH);
  Serial.println("request: /off");
  server.send(200, "text/html", "LED off");
}

void wait_to_feed()
{
  while (millis() - previous_feed < feed_interval)
  {
    delay(100);
  }
  previous_feed = millis();
}

void press_button(int PIN, bool pressed)
{
  if (pressed)
  {
    digitalWrite(PIN, LOW);
    delay(10); // make sure that in the output mode, the value is always LOW
    pinMode(PIN, OUTPUT);
  }
  else
  {
    pinMode(PIN, INPUT);
  }
}

void feed_meal()
{
  Serial.println("request: /meal");
  wait_to_feed();
  press_button(MEAL_PIN, true);
  delay(press_duration);
  press_button(MEAL_PIN, false);
  meal_count += 1;
  server.send(200, "text/plain", "meal count: " + String(meal_count));
}

void feed_snack()
{
  Serial.println("request: /snack");
  wait_to_feed();
  press_button(SNACK_PIN, true);
  delay(press_duration);
  press_button(SNACK_PIN, false);
  snack_count += 1;
  server.send(200, "text/plain", "snack count: " + String(snack_count));
}

void handleNotFound()
{
  digitalWrite(LED_PIN, HIGH);
  pinMode(MEAL_PIN, INPUT);
  pinMode(SNACK_PIN, INPUT);
  String message = "Not Found\n\n";
  message += "URI: ";
  message += server.uri();
  message += "\nMethod: ";
  message += (server.method() == HTTP_GET) ? "GET" : "POST";
  message += "\nArguments: ";
  message += server.args();
  message += "\n";
  for (uint8_t i = 0; i < server.args(); i++)
  {
    message += " " + server.argName(i) + ": " + server.arg(i) + "\n";
  }
  server.send(404, "text/plain", message);
  digitalWrite(LED_PIN, LOW);
}

void setup()
{
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT); // set the LED pin mode

  delay(10);

  // We start by connecting to a WiFi network

  Serial.println();
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected.");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());

  if (MDNS.begin("dry_feeder"))
  {
    Serial.println("MDNS responder started");
  }

  server.on("/", root);

  server.on("/on", on);
  server.on("/off", off);

  server.on("/meal", feed_meal);
  server.on("/snack", feed_snack);

  server.onNotFound(handleNotFound);

  server.begin();
  Serial.println("HTTP server started");
}

void loop()
{
  server.handleClient();
  delay(2); // allow the cpu to switch to other tasks
}
