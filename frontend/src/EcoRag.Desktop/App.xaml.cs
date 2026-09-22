using System.IO;
using System.Windows;
using EcoRag.Desktop.Services;
using EcoRag.Desktop.ViewModels;
using Microsoft.Extensions.DependencyInjection;

namespace EcoRag.Desktop;

public partial class App : Application
{
    public static IServiceProvider ServiceProvider { get; private set; } = null!;

    public App()
    {
        try
        {
            File.WriteAllText(@"C:\Users\shibh\startup_debug.log", $"[App] Constructor entered at {DateTime.Now}\n");
            var services = new ServiceCollection();
            ConfigureServices(services);
            ServiceProvider = services.BuildServiceProvider();
            File.AppendAllText(@"C:\Users\shibh\startup_debug.log", "[App] ServiceProvider built successfully\n");
        }
        catch (Exception ex)
        {
            File.WriteAllText(@"C:\Users\shibh\startup_debug.log", $"[App] Exception in App(): {ex}\n");
        }
    }

    private static void ConfigureServices(IServiceCollection services)
    {
        // HTTP client & API service
        services.AddHttpClient<IEcoRagApiService, EcoRagApiService>();

        // ViewModels
        services.AddSingleton<DashboardViewModel>();
        services.AddSingleton<DocumentsViewModel>();
        services.AddSingleton<ChatViewModel>();
        services.AddSingleton<TelemetryViewModel>();
        services.AddSingleton<SettingsViewModel>();
        services.AddSingleton<MainViewModel>();

        // Main Window
        services.AddSingleton<MainWindow>();
    }

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        var logPath = @"C:\Users\shibh\startup_debug.log";
        File.AppendAllText(logPath, $"[App] OnStartup entered at {DateTime.Now}\n");

        AppDomain.CurrentDomain.UnhandledException += (s, args) =>
        {
            File.AppendAllText(logPath, $"[App] UnhandledException: {args.ExceptionObject}\n");
            MessageBox.Show($"Startup Error: {args.ExceptionObject}", "EcoRAG Error", MessageBoxButton.OK, MessageBoxImage.Error);
        };

        DispatcherUnhandledException += (s, args) =>
        {
            File.AppendAllText(logPath, $"[App] DispatcherUnhandledException: {args.Exception}\n");
            MessageBox.Show($"Dispatcher Error: {args.Exception}", "EcoRAG Dispatcher Error", MessageBoxButton.OK, MessageBoxImage.Error);
        };

        try
        {
            File.AppendAllText(logPath, "[App] Resolving MainWindow...\n");
            var mainWindow = ServiceProvider.GetRequiredService<MainWindow>();
            MainWindow = mainWindow;
            File.AppendAllText(logPath, "[App] Showing MainWindow...\n");
            mainWindow.Show();
            mainWindow.Activate();
            File.AppendAllText(logPath, "[App] MainWindow.Show() called successfully.\n");
        }
        catch (Exception ex)
        {
            File.AppendAllText(logPath, $"[App] Exception in OnStartup: {ex}\n");
            MessageBox.Show($"Startup Exception: {ex.Message}", "EcoRAG Error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    protected override void OnExit(ExitEventArgs e)
    {
        File.AppendAllText(@"C:\Users\shibh\startup_debug.log", $"[App] OnExit called with code {e.ApplicationExitCode}\n");
        base.OnExit(e);
    }
}
