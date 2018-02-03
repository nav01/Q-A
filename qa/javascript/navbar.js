//Sets the active tab of the navbar based on the url.
//Changes the active tabs link to a hash symbol.
$(document).ready(function(){
    var path = window.location.pathname.split('/')[1];
    var navbarTab = $('#' + path);
    if ($(navbarTab).length) {
        $(navbarTab).addClass('active');
        $(navbarTab)[0].firstChild.href = '#';
    }
});
