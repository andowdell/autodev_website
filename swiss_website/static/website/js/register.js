jQuery(document).ready(function ($) {
    $('form').submit(function(event){
        event.preventDefault();
        var data = $(this).serialize();

        $.post("", data).done(function(data){
            if (data['success'] == true)
            {
                $('.bg-success').text('Użytkownik został pomyślnie zarejestrowany.')
                $('.bg-success').fadeIn();
                $('.bg-warning').hide();
            }
            else {
                $('.bg-warning').text(data['error_list'][0]);
                $('.bg-warning').fadeIn();
                $('.bg-success').hide();
            }

        });
    });
});
