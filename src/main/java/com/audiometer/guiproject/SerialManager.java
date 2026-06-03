package com.audiometer.guiproject;
import com.fazecast.jSerialComm.SerialPort;

public class SerialManager {
    private SerialPort activePort; //Variable to hold the hardware port we will connect to
    // Reference to the main UI controller
    private AudiometerController controller;

    public void setController(AudiometerController controller) {
        this.controller = controller;
    }

    //Find all serial ports currently connected to the computer
    public String[] getAvailablePorts() {
        SerialPort[] ports = SerialPort.getCommPorts(); //Retrieve all available ports
        String[] portNames = new String[ports.length]; //Create an empty String array to store the port names
        
        // Loop through the ports and extract only their system names
        for (int i = 0; i < ports.length; i++) {
            portNames[i] = ports[i].getSystemPortName(); 
        }
        
        return portNames; //Send thw list to the frontend developer to populate the ComboBox
    }

    //Connect to the port selected from the GUI and configure parameters
    public boolean connect(String portName) {
        // Instantiate the port object based on the selected name
        activePort = SerialPort.getCommPort(portName.trim());
        System.out.println("tried.");
        
        // Critical Communication Settings (Must match Python/Hardware settings exactly)
        activePort.setBaudRate(9600); // Communication speed
        activePort.setNumDataBits(8);
        activePort.setNumStopBits(SerialPort.ONE_STOP_BIT);
        activePort.setParity(SerialPort.NO_PARITY);
        activePort.setComPortTimeouts(SerialPort.TIMEOUT_READ_SEMI_BLOCKING, 0, 0);
        
        // Attempt to open the port
        if (activePort.openPort()) {
            System.out.println("Successfully connected to port: " + portName);
            return true;
        } else {
            System.out.println("Failed to open port: " + portName + " (It might be used by another application)");
            return false;
        }
    }
   
    //Safely close the active port connection
    public void disconnect() {
        // Check if the port exists and is currently open before trying to close
        if (activePort != null && activePort.isOpen()) {
            activePort.closePort();
            System.out.println("Connection closed safely.");
        }
    }
    /**
     * TASK 4: Sends frequency and intensity data to the hardware/Python script.
     * @param frequency The frequency value in Hz (e.g., 1000)
     * @param intensity The intensity value in dB HL (e.g., 40)
     */
    public void sendToneCommand(int frequency, int intensity) {
        if (activePort != null && activePort.isOpen()) {
            // Construct the message protocol (e.g., "PLAY,1000,40\n")
            String message = "PLAY," + frequency + "," + intensity + "\n";
            
            // Convert the string to bytes and transmit over the serial port
            byte[] writeBuffer = message.getBytes();
            activePort.writeBytes(writeBuffer, writeBuffer.length);
            System.out.println("Sent command: " + message.trim());
        } else {
            System.out.println("Cannot send data. Port is closed!");
        }
    }

    //Starts an asynchronous listener that constantly waits for incoming data.
    public void startListening() {
        if (activePort == null || !activePort.isOpen()) {
            System.out.println("Cannot listen. Port is not open.");
            return;
        }

        // Add a data listener to the active serial port
        activePort.addDataListener(new com.fazecast.jSerialComm.SerialPortDataListener() {
            @Override
            public int getListeningEvents() {
                // Trigger this listener whenever data is available to be read
                return SerialPort.LISTENING_EVENT_DATA_AVAILABLE;
            }

            @Override
            public void serialEvent(com.fazecast.jSerialComm.SerialPortEvent event) {
                if (event.getEventType() != SerialPort.LISTENING_EVENT_DATA_AVAILABLE) {
                    return;
                }

                // Create a buffer to read the incoming bytes
                byte[] readBuffer = new byte[activePort.bytesAvailable()];
                int numRead = activePort.readBytes(readBuffer, readBuffer.length);
                
                if (numRead > 0) {
                    // Convert raw bytes into a readable String
                    String receivedData = new String(readBuffer, 0, numRead).trim();
                    System.out.println("Received raw data from serial: " + receivedData);

                    // Check if the patient pressed the response button
                    if (receivedData.contains("RESPONSE")) {
                        System.out.println("Patient responded! Triggering UI graph update...");
                        
                        // Safely call the UI method from the background thread
                        if (controller != null) {
                            javafx.application.Platform.runLater(() -> {
                                controller.handlePlotAction();
                            });
                        }
                    }
                }
            }
        });
    }
}