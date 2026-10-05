using System.IO;
using System.Windows;
using EcoRag.Desktop.Services;
using EcoRag.Desktop.ViewModels;
using Microsoft.Extensions.DependencyInjection;

namespace EcoRag.Desktop;

public partial class App : Application
{
    public static IServiceProvider ServiceProvider { get; private set; } = null!;
    private static readonly string StartupLogPath = @"C:\Users\shibh\startup_debug.log";
    private static readonly string UiLogPath = Path.Combine(Path.GetTempPath(), "ecorag_ui.log");

    public App()
    {
        try
        {
            LogIssue("INFO", "APP", "constructor", "Constructor entered");
            var services = new ServiceCollection();
            ConfigureServices(services);
            ServiceProvider = services.BuildServiceProvider();
            LogIssue("INFO", "APP", "di", "ServiceProvider built successfully");
        }
        catch (Exception ex)
        {
            LogIssue("ERROR", "APP", ex.GetType().Name, ex.ToString());
        }
    }

    private static void ConfigureServices(IServiceCollection services)
    {
        services.AddHttpClient<IEcoRagApiService, EcoRagApiService>(client =>
        {
            client.Timeout = TimeSpan.FromSeconds(120);
        });

        services.AddSingleton<DashboardViewModel>();
        services.AddSingleton<DocumentsViewModel>();
        services.AddSingleton<ChatViewModel>();
        services.AddSingleton<TelemetryViewModel>();
        services.AddSingleton<SettingsViewModel>();
        services.AddSingleton<MainViewModel>();
        services.AddSingleton<MainWindow>();
    }

    internal static void LogIssue(string level, string component, string error, string message)
    {
        var line =
            $"[{DateTime.Now:O}] [{level}] component={component} error={error} message={message.Replace(Environment.NewLine, " | ")}{Environment.NewLine}";
        try
        {
            File.AppendAllText(StartupLogPath, line);
            File.AppendAllText(UiLogPath, line);
        }
        catch
        {
            // logging must never throw during startup
        }
    }

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        LogIssue("INFO", "APP", "startup", "OnStartup entered");

        AppDomain.CurrentDomain.UnhandledException += (_, args) =>
        {
            LogIssue("ERROR", "UI", "UnhandledException", args.ExceptionObject?.ToString() ?? "unknown");
        };

        DispatcherUnhandledException += (_, args) =>
        {
            LogIssue("ERROR", "UI", args.Exception.GetType().Name, args.Exception.ToString());
            args.Handled = true;
        };

        try
        {
            LogIssue("INFO", "APP", "startup", "Resolving MainWindow");
            var mainWindow = ServiceProvider.GetRequiredService<MainWindow>();
            MainWindow = mainWindow;
            LogIssue("INFO", "APP", "startup", "Showing MainWindow");
            mainWindow.Show();
            mainWindow.Activate();
            LogIssue("INFO", "APP", "startup", "MainWindow.Show succeeded");
        }
        catch (Exception ex)
        {
            LogIssue("ERROR", "UI", ex.GetType().Name, ex.ToString());
            MessageBox.Show(
                $"Startup failed. Details were written to:{Environment.NewLine}{StartupLogPath}{Environment.NewLine}{UiLogPath}{Environment.NewLine}{Environment.NewLine}{ex.Message}",
                "EcoRAG Error",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
        }
    }

    protected override void OnExit(ExitEventArgs e)
    {
        LogIssue("INFO", "APP", "exit", $"OnExit code={e.ApplicationExitCode}");
        base.OnExit(e);
    }
}
