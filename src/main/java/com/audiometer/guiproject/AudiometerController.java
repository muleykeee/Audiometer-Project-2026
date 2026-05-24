package com.audiometer.guiproject;

import javafx.scene.chart.XYChart;
import javafx.scene.control.Label;

public class AudiometerController {

    private AudiometerView view;

    public AudiometerController(AudiometerView view) {
        this.view = view;
        setupEventHandlers();
    }

    private void setupEventHandlers() {
        // Grafiğe Ekle butonuna tıklandığında çalışacak olay
        view.btnPlot.setOnAction(event -> handlePlotAction());

        //buraya view.btnConnect.setOnAction(...) eklenecek
        // Hughson-Westlake buton tıklama olayları
        view.btnDown10.setOnAction(event -> applyHughsonWestlake(-10));
        view.btnUp5.setOnAction(event -> applyHughsonWestlake(5));
    }

    private void handlePlotAction() {
        int currentFreq = view.freqBox.getValue();
        int currentDb = view.dbBox.getValue();
        boolean isRightEar = view.rbRight.isSelected();

        // Odyogram için dB değerini eksiye çeviriyoruz
        XYChart.Data<Number, Number> dataPoint = new XYChart.Data<>(currentFreq, -currentDb);

        Label marker = new Label(isRightEar ? "O" : "X");
        marker.setStyle("-fx-font-weight: bold; -fx-font-size: 16px;  -fx-text-fill: " + (isRightEar ? "red;" : "blue;"));
        dataPoint.setNode(marker);

        if (isRightEar) {
            view.rightEarSeries.getData().add(dataPoint);
        } else {
            view.leftEarSeries.getData().add(dataPoint);
        }
    }
    //yazılım ekibinin koduna göre sadece method çağıracak şekilde düzenlenebilir
    private void applyHughsonWestlake(int change) {
        int currentDb = view.dbBox.getValue();
        int newDb = currentDb + change;

        // BME Takımının kurallarına göre sınırlar: -10 dB ile 120 dB arası
        if (newDb < -10) {
            newDb = -10;
        } else if (newDb > 120) {
            newDb = 120;
        }

        // Hesaplanan yeni değeri ekrandaki kutuya yansıt
        view.dbBox.setValue(newDb);
    }
}