jQuery(document).ready(function ($) {
	// sticky footer

    if ($(window).width() < 960) {
        var width = $('.auction-gallery-main').width();
        $('.auction-gallery-main img').css('maxHeight', 'none');
        $('.auction-gallery-main img').css('maxWidth', width+'px');
     }
     else {
        var height = $('.wrapper').height();
        height-=82;
        $('.wrapper').height(height);

        var thumbs = $('.auction-gallery-thumbs');
        if (thumbs.length > 0)
        {
            console.log($('.auction-gallery-main img'));
            $('.auction-gallery-main img').css('height', thumbs.height());
        }

        setTimeout(function(){ 
            var thumbs = $('.auction-gallery-thumbs');
            if (thumbs.length > 0)
            {
            console.log($('.auction-gallery-main img'));
            $('.auction-gallery-main img').css('height', thumbs.height());
        }
        }, 500);

        setTimeout(function(){ 
            var thumbs = $('.auction-gallery-thumbs');
            if (thumbs.length > 0)
            {
            console.log($('.auction-gallery-main img'));
            $('.auction-gallery-main img').css('height', thumbs.height());
        }
        }, 1500);

        setTimeout(function(){ 
            var thumbs = $('.auction-gallery-thumbs');
            if (thumbs.length > 0)
            {
            console.log($('.auction-gallery-main img'));
            $('.auction-gallery-main img').css('height', thumbs.height());
        }
        }, 2500);
        setTimeout(function(){ 
            var thumbs = $('.auction-gallery-thumbs');
            if (thumbs.length > 0)
            {
            console.log($('.auction-gallery-main img'));
            $('.auction-gallery-main img').css('height', thumbs.height());
        }
        }, 5500);
        setTimeout(function(){ 
            var thumbs = $('.auction-gallery-thumbs');
            if (thumbs.length > 0)
            {
            console.log($('.auction-gallery-main img'));
            $('.auction-gallery-main img').css('height', thumbs.height());
        }
        }, 10000);
     }


});
