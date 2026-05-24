package com.audiometer.guiproject;

import javafx.geometry.Insets;
import javafx.scene.chart.LineChart;
import javafx.scene.chart.NumberAxis;
import javafx.scene.chart.XYChart;
import javafx.scene.control.*;
import javafx.scene.layout.*;

public class AudiometerView {
    private BorderPane root;

    // Dışarıdan erişilmesi gereken arayüz elemanları
    public ComboBox<String> portBox;
    public Button btnConnect;
    public RadioButton rbRight;
    public RadioButton rbLeft;
    public ComboBox<Integer> freqBox;
    public ComboBox<Integer> dbBox;
    public Button btnPlot;
    public Button btnDown10;
    public Button btnUp5;

    // Grafik ve Seriler
    public LineChart<Number, Number> audiogramChart;
    public XYChart.Series<Number, Number> rightEarSeries;
    public XYChart.Series<Number, Number> leftEarSeries;

    public AudiometerView() {
        root = new BorderPane();
        root.setPadding(new Insets(15));

        createTopPanel();
        createLeftPanel();
        createChart();
    }

    private void createTopPanel() {
        HBox topPanel = new HBox(10);
        topPanel.setPadding(new Insets(0, 0, 15, 0));

        portBox = new ComboBox<>();
        portBox.getItems().addAll("COM1", "COM2", "COM3");
        portBox.setPromptText("Port Seçin");

        btnConnect = new Button("Bağlan");

        topPanel.getChildren().addAll(new Label("Seri Port:"), portBox, btnConnect);
        root.setTop(topPanel);
    }

    private void createLeftPanel() {
        VBox leftPanel = new VBox(15);
        leftPanel.setPadding(new Insets(10));
        leftPanel.getStyleClass().add("panel-box");
        leftPanel.setPrefWidth(220);

        Label lblControl = new Label("Test Kontrolleri");
        lblControl.getStyleClass().add("baslik-label");

        ToggleGroup earGroup = new ToggleGroup();
        rbRight = new RadioButton("Sağ Kulak");
        rbLeft = new RadioButton("Sol Kulak");
        rbRight.setToggleGroup(earGroup);
        rbLeft.setToggleGroup(earGroup);
        rbRight.setSelected(true);

        Label lblFreq = new Label("Frekans (Hz):");
        freqBox = new ComboBox<>();
        freqBox.getItems().addAll(250, 500, 1000, 2000, 4000, 8000);
        freqBox.setValue(1000);

        Label lblDb = new Label("Ses Şiddeti (dB):");
        dbBox = new ComboBox<>();
        for (int i = -10; i <= 120; i += 5) {
            dbBox.getItems().add(i);
        }
        dbBox.setValue(40);

        // Hughson-Westlake Hızlı Butonları
        HBox hwBox = new HBox(10);
        btnDown10 = new Button("-10 dB (Duydu)");
        btnDown10.setStyle("-fx-background-color: #f44336; -fx-text-fill: white;"); // Kırmızı uyarıcı

        btnUp5 = new Button("+5 dB (Duymadı)");
        btnUp5.setStyle("-fx-background-color: #2196F3; -fx-text-fill: white;"); // Mavi uyarıcı

        hwBox.getChildren().addAll(btnDown10, btnUp5);

        btnPlot = new Button("Grafiğe Ekle (Test)");
        btnPlot.getStyleClass().add("action-button");

        leftPanel.getChildren().addAll(lblControl, rbRight, rbLeft, new Separator(), lblFreq, freqBox, lblDb, dbBox, hwBox, btnPlot);
        root.setLeft(leftPanel);
    }

    private void createChart() {
        NumberAxis xAxis = new NumberAxis(125, 8000, 1000);
        xAxis.setLabel("Frekans (Hz)");

        NumberAxis yAxis = new NumberAxis(-120, 10, 10);
        yAxis.setLabel("İşitme Eşiği (dB)");

        // Ters Y ekseni hilesi
        yAxis.setTickLabelFormatter(new NumberAxis.DefaultFormatter(yAxis) {
            @Override
            public String toString(Number object) {
                return String.valueOf(-object.intValue());
            }
        });

        audiogramChart = new LineChart<>(xAxis, yAxis);
        audiogramChart.setTitle("Klinik Odyogram");
        audiogramChart.setAnimated(false);

        rightEarSeries = new XYChart.Series<>();
        rightEarSeries.setName("Sağ Kulak (Kırmızı O)");

        leftEarSeries = new XYChart.Series<>();
        leftEarSeries.setName("Sol Kulak (Mavi X)");

        audiogramChart.getData().addAll(rightEarSeries, leftEarSeries);
        root.setCenter(audiogramChart);
    }

    public BorderPane getRoot() {
        return root;
    }
}
