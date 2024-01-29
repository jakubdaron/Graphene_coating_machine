#include <AccelStepper.h>

const int StepX = 2; // Pin configuration of steps for motor X
const int DirX = 5;  // Pin configuration of spinning direction for motor X

const int StepZ = 4; // Pin configuration of steps for motor Z
const int DirZ = 7; // Pin configuration of spinning direction for motor Z
const int EndStopZ = 9; // Pin cofiguration of limit switch for motor Z
int stateZ; // State of limit switch

int val = 0; // Value read by sensor
static String commandBuffer = ""; // Buffer for command sent from Python app
float KGforce = 0; // Force in kilograms
float Gforce = 0;  // Force in grams
int steps = 0; // Value of steps to spin a motor
int calibrationWeigth = 0; // Actual value determined based on the trend line function of the calibration curve
int zero = 0; // Value used to consider mass placed on spinning table
int sum = 0; // Value used for calculations of average measurments in precise downward movement
float reqWeight = 0; // Value of read mass in downward movement (considers value of variable "zero")

char receivedValue;
AccelStepper stepperX(1, StepX, DirX);
AccelStepper stepperZ(2, StepZ, DirZ);

void setup() {
  Serial.begin(9600);
  pinMode(EndStopZ, INPUT_PULLUP);
  pinMode(DirZ, OUTPUT);
  pinMode(StepZ, OUTPUT);

  stepperX.setMaxSpeed(10000); // Max speed of steps per second for motor Z
  stepperX.setAcceleration(500); // Acceleration of motor X

  stepperZ.setMaxSpeed(10000); // Max speed of steps per second for motor Z
  stepperZ.setAcceleration(500); // Acceleration of motor Z
}

void loop() {
    serialEvent();
}

void serialEvent() { // Reading command buffer until the end sign ":" 
    while (Serial.available() > 0) {
        char receivedChar = Serial.read();
        if (receivedChar == ':') { // Found sign of new line or ending previous commend 
            processCommand(commandBuffer); 
            commandBuffer = ""; // Clear buffer after processing
        } else {
            commandBuffer += receivedChar; // Add read sign to commend buffer
        }
    }
}

void processCommand(String command) {
  char firstChar = command.charAt(0);

  if (firstChar == 's') { // Reading once value of calculated mass
    val = analogRead(A5);
    calibrationWeigth = 0.00005 * pow(val, 3) - 0.0206 * pow(val, 2) + 4.3575 * val - 26.459; //Change if own calibration function is needed
    delay(100);
    Serial.println(calibrationWeigth);
  } 
  
  if (firstChar == 'p') { // Spinning the table with desired amount of steps 
    steps = command.substring(1).toInt();
    stepperX.moveTo(steps);
    stepperX.runToPosition();
    while (stepperX.run()) {}
    Serial.println("Koniec");
  } 

  if (firstChar == 'u') { // Moving upwards to limit switch
    digitalWrite(DirZ, HIGH); 
    stateZ = digitalRead(EndStopZ);

    if (stateZ == 1) {
      while (true) {
        for (int i = 0; i < 200; i++) { // Amount of steps on full revolut of motor Z axis
          digitalWrite(StepZ, HIGH);
          delayMicroseconds(1000);  // Delay between steps 
          digitalWrite(StepZ, LOW);
          delayMicroseconds(1000);  // Delay between steps
        }
        stateZ = digitalRead(EndStopZ);
        if (stateZ == 0) { //If limit switch is closed - stop the motor Z axis
          stepperZ.stop();
          break;
        }
      }
    }
    Serial.println("Koniec"); 
  }

  if (firstChar == 'd') { // Moving downwards (limited by pressure sensor)
    val = analogRead(A5);
    zero = 0.00005 * pow(val, 3) - 0.0206 * pow(val, 2) + 4.3575 * val - 26.459; // Change if own calibration function is needed
    digitalWrite(DirZ, LOW); 

    while (true) {
      for (int i = 0; i < 200; i++) { // Amount of steps on full revolut of motor Z axis
        digitalWrite(StepZ, HIGH);
        delayMicroseconds(1000);  // Delay between steps 
        digitalWrite(StepZ, LOW);
        delayMicroseconds(1000);  // Delay between steps
      }
      val = analogRead(A5);
      calibrationWeigth = 0.00005 * pow(val, 3) - 0.0206 * pow(val, 2) + 4.3575 * val - 26.459; // Change if own calibration function is needed
      reqWeight = calibrationWeigth  - zero;
      if (reqWeight > 400) { // If read actual value is high enough - stop the motor Z axis
        stepperZ.stop();
        break;
      }
    }
    Serial.println("Koniec"); 
  }

  if (firstChar == 'm') { // Precise downward movement to get the most accurate mass reading from sensor
    KGforce = command.substring(1).toFloat();
    Gforce = KGforce * 1000;

    if (Gforce >= 500) { // Realise the function only when the value of Gforce was specified
      digitalWrite(DirZ, HIGH); 
      stepperZ.move(500);
      stepperZ.runToPosition();

      val = analogRead(A5);
      calibrationWeigth = 0.00005 * pow(val, 3) - 0.0206 * pow(val, 2) + 4.3575 * val - 26.459; // Change if own calibration function is needed
      reqWeight = calibrationWeigth - zero; 
      delay(70);
      digitalWrite(DirZ, LOW); 
      while (reqWeight < 0.95*Gforce) { // Loop until getting specified Gforce value
        if (reqWeight > 0.7*Gforce) { // Move slower when weight value is getting closer to derired Gforce value
          stepperZ.move(-5);
        }
        else {
          stepperZ.move(-100);
        }
        stepperZ.runToPosition();
        sum = 0;
        reqWeight = 0;
        for (int i = 0; i < 10; i++) { // Make 10 mearurements, than calculate the average value of read weight
          val = analogRead(A5);
          delay(40);
          calibrationWeigth = 0.00005 * pow(val, 3) - 0.0206 * pow(val, 2) + 4.3575 * val - 26.459; // Change if own calibration function is needed
          reqWeight = calibrationWeigth - zero;
          sum = sum + reqWeight;
        }
        reqWeight = sum/10;
      }
    }
    Serial.println("Koniec");
  }

  if (firstChar == 'r') { // Move in Z axis with desired amount of steps
    digitalWrite(DirZ, HIGH); 
    steps = command.substring(1).toInt();
    stepperZ.moveTo(steps);
    stepperZ.runToPosition();
    while (stepperZ.run()) {}
    Serial.println("Koniec");
  }
}
