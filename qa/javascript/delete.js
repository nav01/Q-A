/*
    Delete resources via ajax.  
*/
$(document).ready(function(){
    $('.delete-form').submit(function(event) {
        var form = this;
        event.preventDefault();
        var formData = $(this).serialize();
        $.ajax({
            type: 'POST',
            url: $(this).attr('action'),
            data: formData,
        }).done(function(data, statusText, xhr){
            if(xhr.status == '204'){
                $(form).closest('.resource-container').remove();
            }
        }).fail(function(){
            alert('You do not have the appropriate permissions to perform that operation.');
        });
    });
});
