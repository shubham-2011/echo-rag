using System.Windows.Controls;
using System.Windows.Input;
using EcoRag.Desktop.ViewModels;

namespace EcoRag.Desktop.Views;

public partial class ChatView : UserControl
{
    public ChatView()
    {
        InitializeComponent();
    }

    private void InputQuery_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter && DataContext is ChatViewModel vm)
        {
            if (vm.SendMessageCommand.CanExecute(null))
            {
                vm.SendMessageCommand.Execute(null);
            }
        }
    }
}
