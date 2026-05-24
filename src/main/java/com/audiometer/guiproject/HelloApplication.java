package com.audiometer.guiproject;

import javafx.application.Application;
import javafx.scene.Scene;
import javafx.stage.Stage;

public class HelloApplication extends Application {

    @Override
    public void start(Stage primaryStage) {
        // 1. Görseli oluştur
        AudiometerView view = new AudiometerView();

        // 2. Kontrolcüyü oluştur ve görseli ona bağla
        AudiometerController controller = new AudiometerController(view);

        // 3. Sahneyi kur ve CSS'i ekle
        Scene scene = new Scene(view.getRoot(), 950, 650);

        // Eğer style.css oluşturmadıysan aşağıdaki satırı yoruma alabilirsin (//)
        scene.getStylesheets().add(getClass().getResource("/style.css").toExternalForm());

        primaryStage.setTitle("Audiometer System - Spring 2026");
        primaryStage.setScene(scene);
        primaryStage.show();
    }

    public static void main(String[] args) {
        launch(args);
    }
}