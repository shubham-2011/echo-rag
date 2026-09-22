using System.IO;
using System.Windows;
using EcoRag.Desktop.ViewModels;

namespace EcoRag.Desktop;

public partial class MainWindow : Window
{
    public MainWindow(MainViewModel viewModel)
    {
        var logPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "startup.log");
        File.AppendAllText(logPath, "[MainWindow] Constructor entered\n");

        InitializeComponent();
        File.AppendAllText(logPath, "[MainWindow] InitializeComponent completed\n");

        DataContext = viewModel;
        File.AppendAllText(logPath, "[MainWindow] DataContext set\n");

        Loaded += (s, e) =>
        {
            File.AppendAllText(@"C:\Users\shibh\startup_debug.log", "[MainWindow] Loaded event fired! Window visible on screen!\n");
            Activate();
            Focus();
            Topmost = false;
        };

        Closing += (s, e) =>
        {
            File.AppendAllText(@"C:\Users\shibh\startup_debug.log", $"[MainWindow] Closing event fired! Cancel: {e.Cancel}\n");
        };

        Closed += (s, e) =>
        {
            File.AppendAllText(@"C:\Users\shibh\startup_debug.log", "[MainWindow] Closed event fired!\n");
        };
    }
}