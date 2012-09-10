# To change this template, choose Tools | Templates
# and open the template in the editor.

__author__ = "Ivan"
__date__ = "$10.02.2012. 12:19:56$"


class Mail(object):

    def send_mail(self, message, title, address="bangla456@net.hr"):
        print "Sending mail..........."
        import smtplib
        from email.MIMEMultipart import MIMEMultipart
        from email.MIMEText import MIMEText
        gmailUser = 'zmagsmanas@gmail.com'
        gmailPassword = 'adf123adfg'
        recipient = address

        msg = MIMEMultipart()
        msg['From'] = gmailUser
        msg['To'] = recipient
        msg['Subject'] = "[scraper] " + title
        msg.attach(MIMEText(message))

        mailServer = smtplib.SMTP('smtp.gmail.com', 587)
        mailServer.ehlo()
        mailServer.starttls()
        mailServer.ehlo()
        mailServer.login(gmailUser, gmailPassword)
        mailServer.sendmail(gmailUser, recipient, msg.as_string())
        mailServer.close()
        print "Mail sent"
