# Güvenlik

### Bildirimler
Kullanıcıya 'toast' diye tabir edilen bildirimleri şu şekilde gönderebiliyoruz:

Python/Django:
```
from django.contrib import messages as notifications
notifications.error(request, "bu gün çok <strong>yakışıklısınız</strong>")
```

Javascript (djdict.js):

```
notify("bir şeyler yanlış gitti", "error")
```
Bildirim mesajında nasıl HTML etiketi kullandığıma dikkat edin.
Her ne kadar bu özellik önyüzde kullanışlı mesajlar göstermemize
yarasa da dikkatli kullanılması gerekiyor.

Bildirimler genel mesajlar içerse de, herhangi bir
sebeple kullanıcıdan gelen bir giriyi mesajda göstermek istiyorsanız 
kullanıcıdan gelen giriyi *sanitize* etmeniz gerekiyor, yani özel
HTML karakterlerini kaçış karakterleriyle değiştirmeniz gerekiyor.
Aksi takdirde XSS açığı oluşacaktır.
